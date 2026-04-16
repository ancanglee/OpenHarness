"""Tests for agent persistence — save, load, list, cleanup."""

from __future__ import annotations

import json
import time
import pytest

from openharness.swarm.persistence import (
    AgentPersistence,
    AgentState,
    AgentSummary,
    _safe_filename,
)


@pytest.fixture
def tmp_persistence(tmp_path):
    """Create an AgentPersistence backed by a temp directory."""
    return AgentPersistence(base_dir=tmp_path)


class TestAgentState:
    def test_round_trip(self) -> None:
        state = AgentState(
            agent_id="worker@team1",
            name="worker",
            agent_type="worker",
            status="active",
            created_at="2026-04-15T00:00:00Z",
            tool_use_count=5,
            total_tokens=1000,
            team="team1",
            config={"prompt": "do stuff"},
            metadata={"key": "value"},
        )
        restored = AgentState.from_dict(state.to_dict())
        assert restored.agent_id == state.agent_id
        assert restored.name == state.name
        assert restored.status == state.status
        assert restored.tool_use_count == state.tool_use_count
        assert restored.total_tokens == state.total_tokens
        assert restored.config == state.config
        assert restored.metadata == state.metadata

    def test_from_dict_ignores_unknown_keys(self) -> None:
        data = {"agent_id": "x", "name": "x", "unknown_field": 42}
        state = AgentState.from_dict(data)
        assert state.agent_id == "x"

    def test_defaults(self) -> None:
        state = AgentState(agent_id="a", name="a")
        assert state.status == "active"
        assert state.agent_type == "general-purpose"
        assert state.backend == "in_process"


class TestSafeFilename:
    def test_at_replacement(self) -> None:
        assert _safe_filename("worker@team1") == "worker_at_team1.json"

    def test_slash_replacement(self) -> None:
        assert _safe_filename("a/b") == "a_b.json"

    def test_simple_id(self) -> None:
        assert _safe_filename("agent1") == "agent1.json"


@pytest.mark.asyncio
class TestAgentPersistence:
    async def test_save_and_load(self, tmp_persistence: AgentPersistence) -> None:
        state = AgentState(
            agent_id="w@t",
            name="w",
            status="paused",
            paused_at="2026-04-15T01:00:00Z",
        )
        await tmp_persistence.save_state("w@t", state)
        loaded = await tmp_persistence.load_state("w@t")
        assert loaded is not None
        assert loaded.agent_id == "w@t"
        assert loaded.status == "paused"
        assert loaded.paused_at == "2026-04-15T01:00:00Z"

    async def test_load_missing(self, tmp_persistence: AgentPersistence) -> None:
        result = await tmp_persistence.load_state("nonexistent")
        assert result is None

    async def test_list_agents(self, tmp_persistence: AgentPersistence) -> None:
        for i in range(3):
            state = AgentState(agent_id=f"a{i}", name=f"agent{i}", total_tokens=i * 100)
            await tmp_persistence.save_state(f"a{i}", state)

        agents = await tmp_persistence.list_agents()
        assert len(agents) == 3
        assert all(isinstance(a, AgentSummary) for a in agents)

    async def test_delete_state(self, tmp_persistence: AgentPersistence) -> None:
        state = AgentState(agent_id="del", name="del")
        await tmp_persistence.save_state("del", state)
        assert await tmp_persistence.load_state("del") is not None

        await tmp_persistence.delete_state("del")
        assert await tmp_persistence.load_state("del") is None

    async def test_delete_missing_no_error(self, tmp_persistence: AgentPersistence) -> None:
        await tmp_persistence.delete_state("nope")  # should not raise

    async def test_cleanup_expired(self, tmp_persistence: AgentPersistence) -> None:
        # Create a "completed" agent with old mtime
        state = AgentState(agent_id="old", name="old", status="completed")
        await tmp_persistence.save_state("old", state)

        # Manually set mtime to 100 hours ago
        path = tmp_persistence._path("old")
        old_time = time.time() - 100 * 3600
        import os
        os.utime(path, (old_time, old_time))

        removed = await tmp_persistence.cleanup_expired(max_age_hours=72)
        assert removed == 1
        assert await tmp_persistence.load_state("old") is None

    async def test_cleanup_keeps_recent(self, tmp_persistence: AgentPersistence) -> None:
        state = AgentState(agent_id="new", name="new", status="completed")
        await tmp_persistence.save_state("new", state)

        removed = await tmp_persistence.cleanup_expired(max_age_hours=72)
        assert removed == 0
        assert await tmp_persistence.load_state("new") is not None

    async def test_overwrite_existing(self, tmp_persistence: AgentPersistence) -> None:
        state1 = AgentState(agent_id="x", name="x", status="active", total_tokens=100)
        await tmp_persistence.save_state("x", state1)

        state2 = AgentState(agent_id="x", name="x", status="paused", total_tokens=200)
        await tmp_persistence.save_state("x", state2)

        loaded = await tmp_persistence.load_state("x")
        assert loaded is not None
        assert loaded.status == "paused"
        assert loaded.total_tokens == 200
