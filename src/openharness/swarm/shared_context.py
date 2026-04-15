"""Shared context management for multi-agent collaboration."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from openharness.engine.messages import ConversationMessage


@dataclass
class SharedContext:
    """Manages shared conversation context between collaborating agents.

    Allows a primary agent to share relevant conversation history
    with sub-agents, and merge their results back.
    """

    context_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    _messages: list[ConversationMessage] = field(default_factory=list)
    _results: dict[str, str] = field(default_factory=dict)
    _max_messages: int = 50

    def add_messages(self, messages: list[ConversationMessage]) -> None:
        """Add conversation messages to the shared context."""
        self._messages.extend(messages)
        if len(self._messages) > self._max_messages:
            self._messages = self._messages[-self._max_messages:]

    def get_messages(self, *, max_count: int | None = None) -> list[ConversationMessage]:
        """Retrieve shared messages, optionally limited."""
        if max_count is not None:
            return list(self._messages[-max_count:])
        return list(self._messages)

    def merge_result(self, agent_id: str, result: str) -> None:
        """Store a sub-agent's execution result."""
        self._results[agent_id] = result

    def get_results(self) -> dict[str, str]:
        """Return all collected agent results."""
        return dict(self._results)

    def create_subset(self, indices: list[int]) -> SharedContext:
        """Create a new SharedContext with selected messages."""
        subset_messages = [
            self._messages[i] for i in indices if 0 <= i < len(self._messages)
        ]
        ctx = SharedContext(_max_messages=self._max_messages)
        ctx._messages = subset_messages
        return ctx

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "context_id": self.context_id,
            "messages": [m.to_api_param() for m in self._messages],
            "results": self._results,
            "max_messages": self._max_messages,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SharedContext:
        """Deserialize from dictionary (messages stored as raw dicts)."""
        ctx = cls(
            context_id=data.get("context_id", str(uuid.uuid4())),
            _max_messages=data.get("max_messages", 50),
        )
        ctx._results = data.get("results", {})
        # Note: full message deserialization requires ConversationMessage.from_api_param
        return ctx
