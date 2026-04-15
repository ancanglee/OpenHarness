"""Tests for the Bedrock client."""

from __future__ import annotations

import pytest

from openharness.api.bedrock_client import (
    _normalize_model_id,
    _convert_messages_to_bedrock,
    _convert_tools_to_bedrock,
    _parse_bedrock_assistant_content,
)
from openharness.engine.messages import (
    ConversationMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
)


class TestNormalizeModelId:
    def test_strips_bedrock_prefix(self):
        assert _normalize_model_id("bedrock/anthropic.claude-3-sonnet") == "anthropic.claude-3-sonnet"

    def test_strips_bedrock_prefix_case_insensitive(self):
        assert _normalize_model_id("Bedrock/anthropic.claude-3-sonnet") == "anthropic.claude-3-sonnet"

    def test_no_prefix_unchanged(self):
        assert _normalize_model_id("anthropic.claude-3-sonnet") == "anthropic.claude-3-sonnet"


class TestConvertMessagesToBedrock:
    def test_text_message(self):
        msgs = [ConversationMessage(role="user", content=[TextBlock(text="hello")])]
        result = _convert_messages_to_bedrock(msgs)
        assert result == [{"role": "user", "content": [{"text": "hello"}]}]

    def test_tool_use_message(self):
        msgs = [ConversationMessage(role="assistant", content=[
            ToolUseBlock(id="t1", name="read_file", input={"path": "a.py"}),
        ])]
        result = _convert_messages_to_bedrock(msgs)
        assert result[0]["content"][0]["toolUse"]["name"] == "read_file"
        assert result[0]["content"][0]["toolUse"]["toolUseId"] == "t1"

    def test_tool_result_message(self):
        msgs = [ConversationMessage(role="user", content=[
            ToolResultBlock(tool_use_id="t1", content="file contents"),
        ])]
        result = _convert_messages_to_bedrock(msgs)
        assert result[0]["content"][0]["toolResult"]["toolUseId"] == "t1"

    def test_empty_content_skipped(self):
        msgs = [ConversationMessage(role="user", content=[])]
        result = _convert_messages_to_bedrock(msgs)
        assert result == []


class TestConvertToolsToBedrock:
    def test_basic_tool(self):
        tools = [{"name": "read", "description": "Read a file", "input_schema": {"type": "object"}}]
        result = _convert_tools_to_bedrock(tools)
        assert len(result["tools"]) == 1
        spec = result["tools"][0]["toolSpec"]
        assert spec["name"] == "read"
        assert spec["inputSchema"]["json"] == {"type": "object"}


class TestParsBedrockContent:
    def test_text_block(self):
        blocks = [{"text": "hello"}]
        result = _parse_bedrock_assistant_content(blocks)
        assert len(result) == 1
        assert isinstance(result[0], TextBlock)
        assert result[0].text == "hello"

    def test_tool_use_block(self):
        blocks = [{"toolUse": {"toolUseId": "t1", "name": "read", "input": {"path": "a"}}}]
        result = _parse_bedrock_assistant_content(blocks)
        assert len(result) == 1
        assert isinstance(result[0], ToolUseBlock)
        assert result[0].name == "read"
