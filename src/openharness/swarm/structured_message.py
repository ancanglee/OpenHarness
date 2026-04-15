"""Structured message types for enhanced multi-agent communication."""

from __future__ import annotations

import uuid
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MessageType(str, Enum):
    """Types of structured messages between agents."""
    TASK_ASSIGNMENT = "task_assignment"
    RESULT = "result"
    STATUS_UPDATE = "status_update"
    ERROR = "error"


class Priority(str, Enum):
    """Message priority levels."""
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class TaskStatus(str, Enum):
    """Status of a sub-task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class StructuredMessage:
    """Enhanced message for agent-to-agent communication.

    Supports typed messages with priority, status tracking,
    and references to shared context.
    """

    sender_id: str
    receiver_id: str
    message_type: MessageType
    payload: dict[str, Any]
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: Priority = Priority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    context_refs: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "message_type": self.message_type.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "payload": self.payload,
            "context_refs": self.context_refs,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StructuredMessage:
        """Deserialize from dictionary."""
        return cls(
            message_id=data["message_id"],
            sender_id=data["sender_id"],
            receiver_id=data["receiver_id"],
            message_type=MessageType(data["message_type"]),
            priority=Priority(data.get("priority", "normal")),
            status=TaskStatus(data.get("status", "pending")),
            payload=data.get("payload", {}),
            context_refs=data.get("context_refs", []),
            timestamp=data.get("timestamp", time.time()),
        )

    @classmethod
    def task_assignment(
        cls,
        *,
        sender_id: str,
        receiver_id: str,
        task_description: str,
        context_refs: list[str] | None = None,
        priority: Priority = Priority.NORMAL,
    ) -> StructuredMessage:
        """Create a task assignment message."""
        return cls(
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=MessageType.TASK_ASSIGNMENT,
            payload={"description": task_description},
            priority=priority,
            status=TaskStatus.PENDING,
            context_refs=context_refs or [],
        )

    @classmethod
    def result(
        cls,
        *,
        sender_id: str,
        receiver_id: str,
        task_id: str,
        output: str,
        error: str | None = None,
    ) -> StructuredMessage:
        """Create a result message."""
        status = TaskStatus.FAILED if error else TaskStatus.COMPLETED
        return cls(
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=MessageType.RESULT,
            payload={"task_id": task_id, "output": output, "error": error},
            status=status,
        )
