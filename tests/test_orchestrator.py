"""Tests for the orchestrator module."""

from __future__ import annotations

import pytest

from openharness.coordinator.orchestrator import (
    Orchestrator,
    SpecializedAgent,
    SubAgentResult,
    resolve_execution_order,
)
from openharness.coordinator.task_splitter import SubTask
from openharness.swarm.structured_message import TaskStatus


class TestResolveExecutionOrder:
    def test_no_dependencies_single_layer(self):
        tasks = [
            SubTask(task_id="a", description="A"),
            SubTask(task_id="b", description="B"),
        ]
        layers = resolve_execution_order(tasks)
        assert len(layers) == 1
        assert len(layers[0]) == 2

    def test_sequential_dependencies(self):
        tasks = [
            SubTask(task_id="a", description="A"),
            SubTask(task_id="b", description="B", dependencies=["a"]),
            SubTask(task_id="c", description="C", dependencies=["b"]),
        ]
        layers = resolve_execution_order(tasks)
        assert len(layers) == 3
        assert layers[0][0].task_id == "a"
        assert layers[1][0].task_id == "b"
        assert layers[2][0].task_id == "c"

    def test_parallel_with_shared_dependency(self):
        tasks = [
            SubTask(task_id="a", description="A"),
            SubTask(task_id="b", description="B", dependencies=["a"]),
            SubTask(task_id="c", description="C", dependencies=["a"]),
        ]
        layers = resolve_execution_order(tasks)
        assert len(layers) == 2
        assert layers[0][0].task_id == "a"
        assert len(layers[1]) == 2  # b and c in parallel

    def test_empty_tasks(self):
        assert resolve_execution_order([]) == []

    def test_circular_dependency_handled(self):
        tasks = [
            SubTask(task_id="a", description="A", dependencies=["b"]),
            SubTask(task_id="b", description="B", dependencies=["a"]),
        ]
        layers = resolve_execution_order(tasks)
        # Should still produce layers (circular deps put in one layer)
        assert len(layers) >= 1
        total = sum(len(layer) for layer in layers)
        assert total == 2

    def test_external_dependency_ignored(self):
        """Dependencies on task IDs not in the list are treated as satisfied."""
        tasks = [
            SubTask(task_id="a", description="A", dependencies=["external"]),
        ]
        layers = resolve_execution_order(tasks)
        assert len(layers) == 1
        assert layers[0][0].task_id == "a"


class TestSpecializedAgent:
    def test_create(self):
        agent = SpecializedAgent(
            name="coder",
            system_prompt="You are a coding specialist.",
            model="claude-3-5-haiku",
        )
        assert agent.name == "coder"
        assert agent.model == "claude-3-5-haiku"

    def test_default_tools_empty(self):
        agent = SpecializedAgent(name="test", system_prompt="test")
        assert agent.tools == []
        assert agent.model is None


class TestOrchestratorInit:
    def test_register_agent(self):
        orch = Orchestrator(
            api_client=None,  # type: ignore[arg-type]
            model="test",
        )
        agent = SpecializedAgent(name="coder", system_prompt="code stuff")
        orch.register_agent(agent)
        assert "coder" in orch._agents

    def test_select_agent_by_name(self):
        orch = Orchestrator(
            api_client=None,  # type: ignore[arg-type]
            model="test",
        )
        coder = SpecializedAgent(name="coder", system_prompt="code")
        researcher = SpecializedAgent(name="research", system_prompt="research")
        orch.register_agent(coder)
        orch.register_agent(researcher)

        task = SubTask(description="Write coder logic for the API")
        assert orch._select_agent(task) == coder

        task2 = SubTask(description="Research the best approach")
        assert orch._select_agent(task2) == researcher

        task3 = SubTask(description="Do something generic")
        assert orch._select_agent(task3) is None
