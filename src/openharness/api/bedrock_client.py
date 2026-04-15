"""AWS Bedrock Runtime client using the Converse API."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from functools import partial
from typing import Any, AsyncIterator

from openharness.api.client import (
    ApiMessageCompleteEvent,
    ApiMessageRequest,
    ApiRetryEvent,
    ApiStreamEvent,
    ApiTextDeltaEvent,
)
from openharness.api.errors import (
    AuthenticationFailure,
    OpenHarnessApiError,
    RateLimitFailure,
    RequestFailure,
)
from openharness.api.usage import UsageSnapshot
from openharness.engine.messages import (
    ContentBlock,
    ConversationMessage,
    ImageBlock,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)

log = logging.getLogger(__name__)

MAX_RETRIES = 3
BASE_DELAY = 1.0
MAX_DELAY = 30.0
RETRYABLE_ERROR_CODES = {"ThrottlingException", "ServiceUnavailableException", "InternalServerException"}


def _normalize_model_id(model: str) -> str:
    """Strip optional 'bedrock/' prefix from model identifier."""
    if model.lower().startswith("bedrock/"):
        return model[len("bedrock/"):]
    return model


def _convert_messages_to_bedrock(
    messages: list[ConversationMessage],
) -> list[dict[str, Any]]:
    """Convert internal messages to Bedrock Converse format."""
    bedrock_messages: list[dict[str, Any]] = []
    for msg in messages:
        content_blocks: list[dict[str, Any]] = []
        for block in msg.content:
            if isinstance(block, TextBlock) and block.text:
                content_blocks.append({"text": block.text})
            elif isinstance(block, ImageBlock):
                content_blocks.append({
                    "image": {
                        "format": block.media_type.split("/")[-1] if block.media_type else "png",
                        "source": {"bytes": block.data},
                    }
                })
            elif isinstance(block, ToolUseBlock):
                content_blocks.append({
                    "toolUse": {
                        "toolUseId": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                })
            elif isinstance(block, ToolResultBlock):
                result_content: list[dict[str, Any]] = []
                if block.content:
                    result_content.append({"text": block.content})
                content_blocks.append({
                    "toolResult": {
                        "toolUseId": block.tool_use_id,
                        "content": result_content or [{"text": ""}],
                    }
                })
        if content_blocks:
            bedrock_messages.append({"role": msg.role, "content": content_blocks})
    return bedrock_messages


def _convert_tools_to_bedrock(tools: list[dict[str, Any]]) -> dict[str, Any]:
    """Convert Anthropic tool schemas to Bedrock toolConfig format."""
    tool_specs: list[dict[str, Any]] = []
    for tool in tools:
        tool_specs.append({
            "toolSpec": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "inputSchema": {"json": tool.get("input_schema", {})},
            }
        })
    return {"tools": tool_specs}


def _parse_bedrock_assistant_content(
    content_blocks: list[dict[str, Any]],
) -> list[ContentBlock]:
    """Parse Bedrock response content blocks into internal format."""
    result: list[ContentBlock] = []
    for block in content_blocks:
        if "text" in block:
            result.append(TextBlock(text=block["text"]))
        elif "toolUse" in block:
            tu = block["toolUse"]
            result.append(ToolUseBlock(
                id=tu.get("toolUseId", str(uuid.uuid4())),
                name=tu["name"],
                input=tu.get("input", {}),
            ))
    return result


class BedrockClient:
    """AWS Bedrock Runtime client implementing SupportsStreamingMessages.

    Uses the Converse API for unified model access across all Bedrock models.
    Supports AWS credential chain: environment variables, named profiles, and IAM roles.
    Supports optional Guardrails for content safety filtering.
    """

    def __init__(
        self,
        *,
        region: str | None = None,
        profile: str | None = None,
        role_arn: str | None = None,
        guardrail_id: str | None = None,
        guardrail_version: str | None = None,
    ) -> None:
        try:
            import boto3
            from botocore.config import Config as BotoConfig
        except ImportError as exc:
            raise ImportError(
                "boto3 is required for Bedrock provider. Install with: pip install boto3"
            ) from exc

        self._boto3 = boto3

        # Guardrails config: constructor args take priority, then env vars
        import os
        self._guardrail_id = guardrail_id or os.environ.get("BEDROCK_GUARDRAIL_ID")
        self._guardrail_version = guardrail_version or os.environ.get("BEDROCK_GUARDRAIL_VERSION", "DRAFT")

        session = self._create_session(profile=profile, region=region)

        if role_arn:
            sts = session.client("sts")
            creds = sts.assume_role(
                RoleArn=role_arn, RoleSessionName="openharness-bedrock"
            )["Credentials"]
            session = boto3.Session(
                aws_access_key_id=creds["AccessKeyId"],
                aws_secret_access_key=creds["SecretAccessKey"],
                aws_session_token=creds["SessionToken"],
                region_name=session.region_name,
            )

        resolved_region = session.region_name
        if not resolved_region:
            raise AuthenticationFailure(
                "AWS region not configured. Set AWS_REGION or pass region parameter."
            )
        self._region = resolved_region

        boto_config = BotoConfig(
            retries={"max_attempts": 0},  # We handle retries ourselves
            read_timeout=120,
            connect_timeout=10,
        )
        self._client = session.client(
            "bedrock-runtime", region_name=self._region, config=boto_config
        )

    def _create_session(
        self, *, profile: str | None, region: str | None
    ) -> Any:
        """Create a boto3 Session with the given profile and region."""
        kwargs: dict[str, Any] = {}
        if profile:
            kwargs["profile_name"] = profile
        if region:
            kwargs["region_name"] = region
        return self._boto3.Session(**kwargs)

    async def stream_message(
        self, request: ApiMessageRequest
    ) -> AsyncIterator[ApiStreamEvent]:
        """Yield streamed events for the request, with retry on transient errors."""
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
                if attempt >= MAX_RETRIES or not self._is_retryable(exc):
                    raise self._translate_error(exc) from exc

                delay = min(BASE_DELAY * (2**attempt), MAX_DELAY)
                log.warning(
                    "Bedrock request failed (attempt %d/%d), retrying in %.1fs: %s",
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
            raise self._translate_error(last_error) from last_error


    async def _stream_once(
        self, request: ApiMessageRequest
    ) -> AsyncIterator[ApiStreamEvent]:
        """Single attempt at streaming via Bedrock Converse API."""
        model_id = _normalize_model_id(request.model)
        bedrock_messages = _convert_messages_to_bedrock(request.messages)

        params: dict[str, Any] = {
            "modelId": model_id,
            "messages": bedrock_messages,
            "inferenceConfig": {"maxTokens": request.max_tokens},
        }
        if request.system_prompt:
            params["system"] = [{"text": request.system_prompt}]
        if request.tools:
            params["toolConfig"] = _convert_tools_to_bedrock(request.tools)

        # Add Guardrails if configured (optional — skipped if no guardrail_id)
        if self._guardrail_id:
            params["guardrailConfig"] = {
                "guardrailIdentifier": self._guardrail_id,
                "guardrailVersion": self._guardrail_version or "DRAFT",
                "streamProcessingMode": "async",
            }

        # Run synchronous boto3 call in executor to avoid blocking
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None, partial(self._client.converse_stream, **params)
        )

        collected_text = ""
        collected_tool_uses: list[dict[str, Any]] = []
        current_tool: dict[str, Any] | None = None
        usage_data: dict[str, int] = {}
        stop_reason: str | None = None

        stream = response.get("stream", [])
        for event in stream:
            if "contentBlockStart" in event:
                start = event["contentBlockStart"].get("start", {})
                if "toolUse" in start:
                    current_tool = {
                        "toolUseId": start["toolUse"].get("toolUseId", str(uuid.uuid4())),
                        "name": start["toolUse"].get("name", ""),
                        "input_json": "",
                    }

            elif "contentBlockDelta" in event:
                delta = event["contentBlockDelta"].get("delta", {})
                if "text" in delta:
                    text = delta["text"]
                    collected_text += text
                    yield ApiTextDeltaEvent(text=text)
                elif "toolUse" in delta and current_tool is not None:
                    current_tool["input_json"] += delta["toolUse"].get("input", "")

            elif "contentBlockStop" in event:
                if current_tool is not None:
                    collected_tool_uses.append(current_tool)
                    current_tool = None

            elif "messageStop" in event:
                stop_reason = event["messageStop"].get("stopReason")

            elif "metadata" in event:
                meta_usage = event["metadata"].get("usage", {})
                usage_data = {
                    "input_tokens": meta_usage.get("inputTokens", 0),
                    "output_tokens": meta_usage.get("outputTokens", 0),
                }
                # Handle Guardrails trace in metadata
                guardrail_trace = event["metadata"].get("trace", {}).get("guardrail", {})
                if guardrail_trace:
                    log.debug("Guardrail trace: %s", guardrail_trace)

        # Build final message
        content: list[ContentBlock] = []
        if collected_text:
            content.append(TextBlock(text=collected_text))
        for tu in collected_tool_uses:
            try:
                tool_input = json.loads(tu["input_json"]) if tu["input_json"] else {}
            except (json.JSONDecodeError, TypeError):
                tool_input = {}
            content.append(ToolUseBlock(
                id=tu["toolUseId"],
                name=tu["name"],
                input=tool_input,
            ))

        yield ApiMessageCompleteEvent(
            message=ConversationMessage(role="assistant", content=content),
            usage=UsageSnapshot(
                input_tokens=usage_data.get("input_tokens", 0),
                output_tokens=usage_data.get("output_tokens", 0),
            ),
            stop_reason=stop_reason,
        )

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        """Check if the exception is retryable."""
        error_code = getattr(exc, "response", {})
        if isinstance(error_code, dict):
            code = error_code.get("Error", {}).get("Code", "")
            if code in RETRYABLE_ERROR_CODES:
                return True
        if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
            return True
        return False

    @staticmethod
    def _translate_error(exc: Exception) -> OpenHarnessApiError:
        """Translate boto3/botocore exceptions to OpenHarness errors."""
        error_code = ""
        error_response = getattr(exc, "response", None)
        if isinstance(error_response, dict):
            error_code = error_response.get("Error", {}).get("Code", "")

        msg = str(exc)
        if error_code in {"AccessDeniedException", "UnrecognizedClientException"}:
            return AuthenticationFailure(msg)
        if error_code == "ThrottlingException":
            return RateLimitFailure(msg)
        return RequestFailure(msg)
