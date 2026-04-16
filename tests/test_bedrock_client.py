"""Tests for the Bedrock client — message conversion, model ID resolution, and error handling."""

from __future__ import annotations

import json
import pytest

from openharness.api.bedrock_client import (
    BedrockInferenceMode,
    BedrockModelInfo,
    convert_messages_to_bedrock,
    convert_tools_to_bedrock,
    parse_bedrock_response,
    resolve_model_id,
    _parse_stream_event,
    _StreamState,
    _is_retryable,
    _translate_error,
)
from openharness.api.errors import AuthenticationFailure, RateLimitFailure, RequestFailure
from openharness.engine.messages import (
    ConversationMessage,
    ImageBlock,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)


# ---------------------------------------------------------------------------
# Model ID resolution
# ---------------------------------------------------------------------------


class TestResolveModelId:
    def test_on_demand_model(self) -> None:
        info = resolve_model_id("anthropic.claude-3-sonnet-20240229-v1:0")
        assert info.inference_mode == BedrockInferenceMode.ON_DEMAND
        assert info.resolved_id == "anthropic.claude-3-sonnet-20240229-v1:0"

    def test_system_profile_us(self) -> None:
        info = resolve_model_id("us.anthropic.claude-3-sonnet-20240229-v1:0")
        assert info.inference_mode == BedrockInferenceMode.SYSTEM_PROFILE

    def test_system_profile_eu(self) -> None:
        info = resolve_model_id("eu.anthropic.claude-3-sonnet-20240229-v1:0")
        assert info.inference_mode == BedrockInferenceMode.SYSTEM_PROFILE

    def test_application_profile_arn(self) -> None:
        arn = "arn:aws:bedrock:us-east-1:123456789012:application-inference-profile/abc123"
        info = resolve_model_id(arn)
        assert info.inference_mode == BedrockInferenceMode.APPLICATION_PROFILE
        assert info.resolved_id == arn

    def test_plain_model_id(self) -> None:
        info = resolve_model_id("meta.llama3-70b-instruct-v1:0")
        assert info.inference_mode == BedrockInferenceMode.ON_DEMAND

    def test_idempotent(self) -> None:
        """resolve_model_id(resolve_model_id(x).resolved_id) == resolve_model_id(x)."""
        for model_id in [
            "anthropic.claude-3-sonnet-20240229-v1:0",
            "us.anthropic.claude-3-sonnet-20240229-v1:0",
            "arn:aws:bedrock:us-east-1:123:application-inference-profile/x",
        ]:
            first = resolve_model_id(model_id)
            second = resolve_model_id(first.resolved_id)
            assert first.inference_mode == second.inference_mode
            assert first.resolved_id == second.resolved_id

    def test_empty_model_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            resolve_model_id("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            resolve_model_id("   ")


# ---------------------------------------------------------------------------
# Message conversion
# ---------------------------------------------------------------------------


class TestConvertMessagesToBedrock:
    def test_simple_user_message(self) -> None:
        msgs = [ConversationMessage.from_user_text("Hello")]
        bedrock_msgs, system = convert_messages_to_bedrock(msgs, None)
        assert len(bedrock_msgs) == 1
        assert bedrock_msgs[0]["role"] == "user"
        assert bedrock_msgs[0]["content"] == [{"text": "Hello"}]
        assert system is None

    def test_system_prompt(self) -> None:
        msgs = [ConversationMessage.from_user_text("Hi")]
        _, system = convert_messages_to_bedrock(msgs, "You are helpful.")
        assert system == [{"text": "You are helpful."}]

    def test_empty_system_prompt(self) -> None:
        msgs = [ConversationMessage.from_user_text("Hi")]
        _, system = convert_messages_to_bedrock(msgs, "")
        assert system is None

    def test_tool_use_block(self) -> None:
        msg = ConversationMessage(
            role="assistant",
            content=[ToolUseBlock(id="tu_1", name="bash", input={"command": "ls"})],
        )
        bedrock_msgs, _ = convert_messages_to_bedrock([msg], None)
        tu = bedrock_msgs[0]["content"][0]["toolUse"]
        assert tu["toolUseId"] == "tu_1"
        assert tu["name"] == "bash"
        assert tu["input"] == {"command": "ls"}

    def test_tool_result_block(self) -> None:
        msg = ConversationMessage(
            role="user",
            content=[ToolResultBlock(tool_use_id="tu_1", content="output")],
        )
        bedrock_msgs, _ = convert_messages_to_bedrock([msg], None)
        tr = bedrock_msgs[0]["content"][0]["toolResult"]
        assert tr["toolUseId"] == "tu_1"
        assert tr["content"] == [{"text": "output"}]

    def test_tool_result_error(self) -> None:
        msg = ConversationMessage(
            role="user",
            content=[ToolResultBlock(tool_use_id="tu_1", content="fail", is_error=True)],
        )
        bedrock_msgs, _ = convert_messages_to_bedrock([msg], None)
        tr = bedrock_msgs[0]["content"][0]["toolResult"]
        assert tr["status"] == "error"

    def test_merge_consecutive_same_role(self) -> None:
        msgs = [
            ConversationMessage.from_user_text("A"),
            ConversationMessage.from_user_text("B"),
        ]
        bedrock_msgs, _ = convert_messages_to_bedrock(msgs, None)
        assert len(bedrock_msgs) == 1
        assert len(bedrock_msgs[0]["content"]) == 2

    def test_empty_text_filtered(self) -> None:
        msg = ConversationMessage(role="user", content=[TextBlock(text="")])
        bedrock_msgs, _ = convert_messages_to_bedrock([msg], None)
        assert len(bedrock_msgs) == 0


# ---------------------------------------------------------------------------
# Tool conversion
# ---------------------------------------------------------------------------


class TestConvertToolsToBedrock:
    def test_basic_tool(self) -> None:
        tools = [{"name": "bash", "description": "Run shell", "input_schema": {"type": "object"}}]
        result = convert_tools_to_bedrock(tools)
        spec = result["tools"][0]["toolSpec"]
        assert spec["name"] == "bash"
        assert spec["description"] == "Run shell"
        assert spec["inputSchema"]["json"] == {"type": "object"}


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


class TestParsBedrockResponse:
    def test_text_response(self) -> None:
        response = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": "Hello!"}],
                },
            },
            "stopReason": "end_turn",
            "usage": {"inputTokens": 10, "outputTokens": 5},
        }
        msg = parse_bedrock_response(response)
        assert msg.role == "assistant"
        assert msg.text == "Hello!"

    def test_tool_use_response(self) -> None:
        response = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {"text": "Let me run that."},
                        {"toolUse": {"toolUseId": "tu_1", "name": "bash", "input": {"command": "ls"}}},
                    ],
                },
            },
        }
        msg = parse_bedrock_response(response)
        assert len(msg.content) == 2
        assert msg.tool_uses[0].name == "bash"


# ---------------------------------------------------------------------------
# Stream event parsing
# ---------------------------------------------------------------------------


class TestStreamParsing:
    def test_text_delta(self) -> None:
        state = _StreamState()
        event = {"contentBlockDelta": {"contentBlockIndex": 0, "delta": {"text": "Hi"}}}
        result = _parse_stream_event(event, state)
        assert result is not None
        assert result.text == "Hi"  # type: ignore[attr-defined]
        assert state.collected_text == "Hi"

    def test_tool_use_start_and_delta(self) -> None:
        state = _StreamState()
        start_event = {
            "contentBlockStart": {
                "contentBlockIndex": 1,
                "start": {"toolUse": {"toolUseId": "tu_1", "name": "bash"}},
            },
        }
        _parse_stream_event(start_event, state)
        assert state.tool_calls[1]["id"] == "tu_1"
        assert state.tool_calls[1]["name"] == "bash"

        delta_event = {
            "contentBlockDelta": {
                "contentBlockIndex": 1,
                "delta": {"toolUse": {"input": '{"command":'}},
            },
        }
        _parse_stream_event(delta_event, state)

        delta_event2 = {
            "contentBlockDelta": {
                "contentBlockIndex": 1,
                "delta": {"toolUse": {"input": '"ls"}'}},
            },
        }
        _parse_stream_event(delta_event2, state)
        assert state.tool_calls[1]["arguments"] == '{"command":"ls"}'

    def test_metadata_usage(self) -> None:
        state = _StreamState()
        event = {"metadata": {"usage": {"inputTokens": 100, "outputTokens": 50}}}
        _parse_stream_event(event, state)
        assert state.input_tokens == 100
        assert state.output_tokens == 50

    def test_stop_reason(self) -> None:
        state = _StreamState()
        event = {"messageStop": {"stopReason": "end_turn"}}
        _parse_stream_event(event, state)
        assert state.stop_reason == "end_turn"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_access_denied_not_retryable(self) -> None:
        exc = _make_client_error("AccessDeniedException")
        assert not _is_retryable(exc)

    def test_throttling_retryable(self) -> None:
        exc = _make_client_error("ThrottlingException")
        assert _is_retryable(exc)

    def test_translate_access_denied(self) -> None:
        exc = _make_client_error("AccessDeniedException")
        result = _translate_error(exc)
        assert isinstance(result, AuthenticationFailure)

    def test_translate_throttling(self) -> None:
        exc = _make_client_error("ThrottlingException")
        result = _translate_error(exc)
        assert isinstance(result, RateLimitFailure)

    def test_translate_generic(self) -> None:
        exc = _make_client_error("ValidationException")
        result = _translate_error(exc)
        assert isinstance(result, RequestFailure)

    def test_connection_error_retryable(self) -> None:
        assert _is_retryable(ConnectionError("reset"))
        assert _is_retryable(TimeoutError("timeout"))


def _make_client_error(code: str) -> Exception:
    """Create a mock boto3 ClientError-like exception."""
    exc = Exception(f"AWS error: {code}")
    exc.response = {"Error": {"Code": code, "Message": f"Test {code}"}}  # type: ignore[attr-defined]
    return exc
