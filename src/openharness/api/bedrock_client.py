"""AWS Bedrock Converse API client for OpenHarness.

Supports three invocation modes:
  - On-demand: direct model ID (e.g. ``anthropic.claude-3-sonnet-20240229-v1:0``)
  - System-defined inference profile: cross-region (e.g. ``us.anthropic.claude-3-sonnet-20240229-v1:0``)
  - Application inference profile: custom ARN

Uses boto3 by default for SigV4 signing and credential chain resolution.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import random
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator

from openharness.api.client import (
    ApiMessageCompleteEvent,
    ApiMessageRequest,
    ApiRetryEvent,
    ApiStreamEvent,
    ApiTextDeltaEvent,
    BASE_DELAY,
    MAX_DELAY,
    MAX_RETRIES,
)
from openharness.api.errors import (
    AuthenticationFailure,
    OpenHarnessApiError,
    RateLimitFailure,
    RequestFailure,
)
from openharness.api.usage import UsageSnapshot
from openharness.engine.messages import (
    ConversationMessage,
    ContentBlock,
    ImageBlock,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)

log = logging.getLogger(__name__)

# Region prefixes used by system-defined inference profiles.
_SYSTEM_PROFILE_PREFIXES = frozenset({"us", "eu", "ap", "ca", "sa", "me", "af"})

# Pattern: ``{region_prefix}.{provider}.{model}``
_SYSTEM_PROFILE_RE = re.compile(
    r"^(" + "|".join(sorted(_SYSTEM_PROFILE_PREFIXES)) + r")\.[a-z]",
)

# Pattern: Bedrock on-demand model ID ``{provider}.{model}``
_ON_DEMAND_RE = re.compile(r"^[a-z][a-z0-9-]*\.[a-z]")

_RETRYABLE_ERROR_CODES = frozenset({
    "ThrottlingException",
    "ServiceUnavailableException",
    "InternalServerException",
    "ModelTimeoutException",
})


# ---------------------------------------------------------------------------
# Inference mode
# ---------------------------------------------------------------------------


class BedrockInferenceMode(str, Enum):
    ON_DEMAND = "on_demand"
    SYSTEM_PROFILE = "system_profile"
    APPLICATION_PROFILE = "application_profile"


@dataclass(frozen=True)
class BedrockModelInfo:
    raw_id: str
    resolved_id: str
    inference_mode: BedrockInferenceMode


# ---------------------------------------------------------------------------
# Message conversion helpers (pure functions)
# ---------------------------------------------------------------------------


def convert_messages_to_bedrock(
    messages: list[ConversationMessage],
    system_prompt: str | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]] | None]:
    """Convert OpenHarness messages to Bedrock Converse format.

    Returns ``(messages, system)`` where *system* is ``None`` when no prompt
    is provided.
    """
    bedrock_messages: list[dict[str, Any]] = []

    for msg in messages:
        content = _convert_content_blocks(msg.content, msg.role)
        if not content:
            continue

        # Bedrock requires alternating roles.  Merge consecutive same-role.
        if bedrock_messages and bedrock_messages[-1]["role"] == msg.role:
            bedrock_messages[-1]["content"].extend(content)
        else:
            bedrock_messages.append({"role": msg.role, "content": content})

    system = [{"text": system_prompt}] if system_prompt else None
    return bedrock_messages, system


def _convert_content_blocks(
    blocks: list[ContentBlock],
    role: str,
) -> list[dict[str, Any]]:
    """Convert a list of OpenHarness content blocks to Bedrock format."""
    result: list[dict[str, Any]] = []
    for block in blocks:
        converted = _convert_single_block(block, role)
        if converted is not None:
            result.append(converted)
    return result


def _convert_single_block(
    block: ContentBlock,
    role: str,
) -> dict[str, Any] | None:
    if isinstance(block, TextBlock):
        if not block.text:
            return None
        return {"text": block.text}

    if isinstance(block, ImageBlock):
        try:
            image_bytes = base64.b64decode(block.data)
        except Exception:
            log.warning("Failed to decode base64 image data, skipping image block")
            return None
        fmt = block.media_type.removeprefix("image/")
        return {
            "image": {
                "format": fmt,
                "source": {"bytes": image_bytes},
            },
        }

    if isinstance(block, ToolUseBlock):
        return {
            "toolUse": {
                "toolUseId": block.id,
                "name": block.name,
                "input": block.input,
            },
        }

    if isinstance(block, ToolResultBlock):
        content_items: list[dict[str, Any]] = [{"text": block.content}]
        result: dict[str, Any] = {
            "toolResult": {
                "toolUseId": block.tool_use_id,
                "content": content_items,
            },
        }
        if block.is_error:
            result["toolResult"]["status"] = "error"
        return result

    return None


def convert_tools_to_bedrock(tools: list[dict[str, Any]]) -> dict[str, Any]:
    """Convert Anthropic-format tool definitions to Bedrock toolConfig."""
    bedrock_tools: list[dict[str, Any]] = []
    for tool in tools:
        bedrock_tools.append({
            "toolSpec": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "inputSchema": {"json": tool.get("input_schema", {})},
            },
        })
    return {"tools": bedrock_tools}


def parse_bedrock_response(response: dict[str, Any]) -> ConversationMessage:
    """Parse a Bedrock Converse (non-streaming) response."""
    output = response.get("output", {})
    message = output.get("message", {})
    role = message.get("role", "assistant")
    raw_content = message.get("content", [])
    content = _parse_bedrock_content_blocks(raw_content)
    return ConversationMessage(role=role, content=content)


def _parse_bedrock_content_blocks(raw_blocks: list[dict[str, Any]]) -> list[ContentBlock]:
    """Parse Bedrock content blocks into OpenHarness types."""
    content: list[ContentBlock] = []
    for raw in raw_blocks:
        if "text" in raw:
            content.append(TextBlock(text=raw["text"]))
        elif "toolUse" in raw:
            tu = raw["toolUse"]
            content.append(ToolUseBlock(
                id=tu.get("toolUseId", ""),
                name=tu.get("name", ""),
                input=tu.get("input", {}),
            ))
    return content


# ---------------------------------------------------------------------------
# Model ID resolution
# ---------------------------------------------------------------------------


def resolve_model_id(model: str) -> BedrockModelInfo:
    """Resolve a user-provided model string into Bedrock model info."""
    model = model.strip()
    if not model:
        raise ValueError("Bedrock model ID must not be empty")

    # Application inference profile (ARN)
    if model.startswith("arn:"):
        return BedrockModelInfo(
            raw_id=model,
            resolved_id=model,
            inference_mode=BedrockInferenceMode.APPLICATION_PROFILE,
        )

    # System-defined inference profile (region prefix)
    if _SYSTEM_PROFILE_RE.match(model):
        return BedrockModelInfo(
            raw_id=model,
            resolved_id=model,
            inference_mode=BedrockInferenceMode.SYSTEM_PROFILE,
        )

    # On-demand (provider.model format or plain ID)
    return BedrockModelInfo(
        raw_id=model,
        resolved_id=model,
        inference_mode=BedrockInferenceMode.ON_DEMAND,
    )


# ---------------------------------------------------------------------------
# Stream parser
# ---------------------------------------------------------------------------


@dataclass
class _StreamState:
    """Mutable state for ConverseStream event parsing."""

    collected_text: str = ""
    tool_calls: dict[int, dict[str, Any]] = field(default_factory=dict)
    stop_reason: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0


# ---------------------------------------------------------------------------
# BedrockClient
# ---------------------------------------------------------------------------


class BedrockClient:
    """AWS Bedrock Converse API client.

    Implements the ``SupportsStreamingMessages`` protocol so it can be used
    as a drop-in replacement for ``AnthropicApiClient`` or
    ``OpenAICompatibleClient`` in the agent loop.
    """

    def __init__(
        self,
        region: str,
        *,
        profile_name: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
    ) -> None:
        self._region = region
        self._profile_name = profile_name
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        self._aws_session_token = aws_session_token
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazily create the boto3 bedrock-runtime client."""
        if self._client is not None:
            return self._client

        try:
            import boto3
        except ImportError as exc:
            raise RequestFailure(
                "boto3 is required for Bedrock provider. "
                "Install it with: pip install boto3"
            ) from exc

        if self._profile_name:
            session = boto3.Session(profile_name=self._profile_name, region_name=self._region)
        elif self._aws_access_key_id and self._aws_secret_access_key:
            session = boto3.Session(
                aws_access_key_id=self._aws_access_key_id,
                aws_secret_access_key=self._aws_secret_access_key,
                aws_session_token=self._aws_session_token,
                region_name=self._region,
            )
        else:
            session = boto3.Session(region_name=self._region)

        self._client = session.client("bedrock-runtime")
        return self._client

    async def stream_message(
        self, request: ApiMessageRequest
    ) -> AsyncGenerator[ApiStreamEvent, None]:
        """Stream a Bedrock ConverseStream response, yielding ApiStreamEvents."""
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                async for event in self._stream_once(request):
                    yield event
                return
            except OpenHarnessApiError:
                raise
            except Exception as exc:
                last_error = exc
                if attempt >= MAX_RETRIES or not _is_retryable(exc):
                    raise _translate_error(exc) from exc

                delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                delay += random.uniform(0, delay * 0.25)  # jitter
                log.warning(
                    "Bedrock API request failed (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1, MAX_RETRIES + 1, delay, exc,
                )
                yield ApiRetryEvent(
                    message=str(exc),
                    attempt=attempt + 1,
                    max_attempts=MAX_RETRIES + 1,
                    delay_seconds=delay,
                )
                await asyncio.sleep(delay)

        if last_error is not None:
            raise _translate_error(last_error) from last_error

    async def _stream_once(
        self, request: ApiMessageRequest
    ) -> AsyncGenerator[ApiStreamEvent, None]:
        """Single attempt: stream a Bedrock ConverseStream call."""
        model_info = resolve_model_id(request.model)
        bedrock_messages, system = convert_messages_to_bedrock(
            request.messages, request.system_prompt,
        )

        params: dict[str, Any] = {
            "modelId": model_info.resolved_id,
            "messages": bedrock_messages,
            "inferenceConfig": {"maxTokens": request.max_tokens},
        }
        if system:
            params["system"] = system
        if request.tools:
            params["toolConfig"] = convert_tools_to_bedrock(request.tools)

        loop = asyncio.get_running_loop()
        client = self._get_client()

        # boto3 is synchronous — run in executor.
        response = await loop.run_in_executor(
            None, lambda: client.converse_stream(**params),
        )

        state = _StreamState()
        stream = response.get("stream", [])

        # Process the synchronous event iterator in the executor, bridging
        # events to the async world via a queue.  Use call_soon_threadsafe
        # for thread-safe queue writes from the executor thread.
        queue: asyncio.Queue[ApiStreamEvent | None | Exception] = asyncio.Queue()

        def _consume_stream() -> None:
            try:
                for event in stream:
                    api_event = _parse_stream_event(event, state)
                    if api_event is not None:
                        loop.call_soon_threadsafe(queue.put_nowait, api_event)
                # Signal completion.
                _build_final_event(state, queue, loop)
                loop.call_soon_threadsafe(queue.put_nowait, None)
            except Exception as exc:
                loop.call_soon_threadsafe(queue.put_nowait, exc)

        consume_task = loop.run_in_executor(None, _consume_stream)

        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                if isinstance(item, Exception):
                    raise item
                yield item
        finally:
            # Ensure the executor thread completes to prevent leaks.
            await consume_task


def _parse_stream_event(
    event: dict[str, Any],
    state: _StreamState,
) -> ApiStreamEvent | None:
    """Parse a single ConverseStream event, updating *state* in place."""
    if "contentBlockDelta" in event:
        delta = event["contentBlockDelta"].get("delta", {})
        idx = event["contentBlockDelta"].get("contentBlockIndex", 0)

        if "text" in delta:
            text = delta["text"]
            state.collected_text += text
            return ApiTextDeltaEvent(text=text)

        if "toolUse" in delta:
            if idx not in state.tool_calls:
                state.tool_calls[idx] = {"id": "", "name": "", "arguments": ""}
            state.tool_calls[idx]["arguments"] += delta["toolUse"].get("input", "")

    elif "contentBlockStart" in event:
        start = event["contentBlockStart"].get("start", {})
        idx = event["contentBlockStart"].get("contentBlockIndex", 0)
        if "toolUse" in start:
            state.tool_calls[idx] = {
                "id": start["toolUse"].get("toolUseId", ""),
                "name": start["toolUse"].get("name", ""),
                "arguments": "",
            }

    elif "messageStop" in event:
        state.stop_reason = event["messageStop"].get("stopReason")

    elif "metadata" in event:
        usage = event["metadata"].get("usage", {})
        state.input_tokens = usage.get("inputTokens", 0)
        state.output_tokens = usage.get("outputTokens", 0)

    return None


def _build_final_event(
    state: _StreamState,
    queue: asyncio.Queue[Any],
    loop: asyncio.AbstractEventLoop,
) -> None:
    """Build the final ApiMessageCompleteEvent from accumulated state."""
    content: list[ContentBlock] = []
    if state.collected_text:
        content.append(TextBlock(text=state.collected_text))

    for idx in sorted(state.tool_calls.keys()):
        tc = state.tool_calls[idx]
        if not tc["name"]:
            continue
        try:
            args = json.loads(tc["arguments"]) if tc["arguments"] else {}
        except (json.JSONDecodeError, TypeError):
            args = {}
        content.append(ToolUseBlock(
            id=tc["id"] or f"toolu_{idx}",
            name=tc["name"],
            input=args,
        ))

    final_message = ConversationMessage(role="assistant", content=content)
    loop.call_soon_threadsafe(queue.put_nowait, ApiMessageCompleteEvent(
        message=final_message,
        usage=UsageSnapshot(
            input_tokens=state.input_tokens,
            output_tokens=state.output_tokens,
        ),
        stop_reason=state.stop_reason,
    ))


# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------


def _is_retryable(exc: Exception) -> bool:
    """Check if a boto3 exception is retryable."""
    error_code = _get_error_code(exc)
    if error_code in _RETRYABLE_ERROR_CODES:
        return True
    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        return True
    return False


def _get_error_code(exc: Exception) -> str:
    """Extract the AWS error code from a boto3 ClientError."""
    response = getattr(exc, "response", None)
    if response and isinstance(response, dict):
        return response.get("Error", {}).get("Code", "")
    return ""


def _translate_error(exc: Exception) -> OpenHarnessApiError:
    """Translate a boto3 exception into an OpenHarness error."""
    error_code = _get_error_code(exc)
    msg = str(exc)

    if error_code in {"AccessDeniedException", "UnrecognizedClientException"}:
        return AuthenticationFailure(f"Bedrock auth error: {msg}")
    if error_code == "ThrottlingException":
        return RateLimitFailure(f"Bedrock rate limit: {msg}")
    if _is_retryable(exc):
        return RequestFailure(f"Bedrock API error (transient): {msg}")
    return RequestFailure(f"Bedrock API error: {msg}")
