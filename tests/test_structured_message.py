"""Tests for structured message types."""

from __future__ import annotations

import pytest

from openharness.swarm.structured_message import (
    MessageType,
    Priority,
    TaskStatus,
    StructuredMessage,
)


class TestStructuredMessage:
    def test_create_basic(self):
        msg = StructuredMessage(
            sender_id="agent-1",
            receiver_id="agent-2",
            message_type=MessageType.TASK_ASSIGNMENT,
            payload={"description": "do something"},
        )
        assert msg.sender_id == "agent-1"
        assert msg.priority == Priority.NORMAL
        assert msg.status == TaskStatus.PENDING

    def test_roundtrip_serialization(self):
        msg = StructuredMessage(
            sender_id="a",
            receiver_id="b",
            message_type=MessageType.RESULT,
            payload={"output": "done"},
            priority=Priority.HIGH,
            status=TaskStatus.COMPLETED,
            context_refs=["ctx-1"],
        )
        data = msg.to_dict()
        restored = StructuredMessage.from_dict(data)
        assert restored.message_id == msg.message_id
        assert restored.message_type == MessageType.RESULT
        assert restored.priority == Priority.HIGH
        assert restored.status == TaskStatus.COMPLETED
        assert restored.context_refs == ["ctx-1"]

    def test_task_assignment_factory(self):
        msg = StructuredMessage.task_assignment(
            sender_id="main",
            receiver_id="worker",
            task_description="implement feature X",
            priority=Priority.HIGH,
        )
        assert msg.message_type == MessageType.TASK_ASSIGNMENT
        assert msg.payload["description"] == "implement feature X"
        assert msg.priority == Priority.HIGH

    def test_result_factory_success(self):
        msg = StructuredMessage.result(
            sender_id="worker",
            receiver_id="main",
            task_id="t1",
            output="completed successfully",
        )
        assert msg.message_type == MessageType.RESULT
        assert msg.status == TaskStatus.COMPLETED
        assert msg.payload["error"] is None

    def test_result_factory_failure(self):
        msg = StructuredMessage.result(
            sender_id="worker",
            receiver_id="main",
            task_id="t1",
            output="",
            error="something broke",
        )
        assert msg.status == TaskStatus.FAILED
        assert msg.payload["error"] == "something broke"
