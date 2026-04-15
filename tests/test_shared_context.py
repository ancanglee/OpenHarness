"""Tests for shared context management."""

from __future__ import annotations

import pytest

from openharness.swarm.shared_context import SharedContext
from openharness.engine.messages import ConversationMessage, TextBlock


def _make_msg(text: str, role: str = "user") -> ConversationMessage:
    return ConversationMessage(role=role, content=[TextBlock(text=text)])


class TestSharedContext:
    def test_add_and_get_messages(self):
        ctx = SharedContext()
        msgs = [_make_msg("hello"), _make_msg("world")]
        ctx.add_messages(msgs)
        assert len(ctx.get_messages()) == 2

    def test_max_messages_enforced(self):
        ctx = SharedContext(_max_messages=3)
        msgs = [_make_msg(f"msg-{i}") for i in range(5)]
        ctx.add_messages(msgs)
        result = ctx.get_messages()
        assert len(result) == 3
        # Should keep the last 3
        assert result[0].text == "msg-2"

    def test_get_messages_with_limit(self):
        ctx = SharedContext()
        ctx.add_messages([_make_msg(f"m{i}") for i in range(10)])
        result = ctx.get_messages(max_count=3)
        assert len(result) == 3

    def test_merge_result(self):
        ctx = SharedContext()
        ctx.merge_result("agent-1", "done task A")
        ctx.merge_result("agent-2", "done task B")
        results = ctx.get_results()
        assert results == {"agent-1": "done task A", "agent-2": "done task B"}

    def test_create_subset(self):
        ctx = SharedContext()
        ctx.add_messages([_make_msg(f"m{i}") for i in range(5)])
        subset = ctx.create_subset([1, 3])
        msgs = subset.get_messages()
        assert len(msgs) == 2
        assert msgs[0].text == "m1"
        assert msgs[1].text == "m3"

    def test_create_subset_out_of_range(self):
        ctx = SharedContext()
        ctx.add_messages([_make_msg("only")])
        subset = ctx.create_subset([0, 5, 10])
        assert len(subset.get_messages()) == 1

    def test_to_dict(self):
        ctx = SharedContext()
        ctx.merge_result("a1", "result")
        data = ctx.to_dict()
        assert "context_id" in data
        assert data["results"] == {"a1": "result"}
