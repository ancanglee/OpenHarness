"""Orchestrator-subagent pattern for multi-agent coordination.

Implements patterns from Anthropic's multi-agent best practices:
- Context protection: each subagent gets isolated, focused context
- Parallelization: independent tasks run via asyncio.gather
- Specialization: agents have focused tools/prompts/models
- Verification: dedicated verification subagent validates work
- Context-centric decomposition: split by context boundaries, not problem type
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from openharness.api.client import (
    ApiMessageRequest,
    ApiTextDeltaEvent,
    ApiMessageCompleteEvent,
    SupportsStreamingMessages,
)
from openharness.engine.messages import ConversationMessage
from openharness.swarm.shared_context import SharedContext
from openharness.swarm.structured_message import TaskStatus
from openharness.coordinator.task_splitter import SubTask, SubTaskResult, TaskSplitter

log = logging.getLogger(__name__)


@dataclass
class SpecializedAgent:
    """A specialized subagent configuration.

    Each agent has focused tools and prompts matched to its responsibilities,
    following Anthropic's specialization pattern.
    """

    name: str
    system_prompt: str
    tools: list[dict[str, Any]] = field(default_factory=list)
    model: str | None = None  # None = inherit from orchestrator


@dataclass
class SubAgentResult:
    """Result from a subagent execution."""

    agent_name: str
    task: SubTask
    output: str
    status: TaskStatus
    error: str | None = None
    tokens_used: int = 0


async def run_subagent(
    *,
    api_client: SupportsStreamingMessages,
    model: str,
    agent: SpecializedAgent | None,
    task: SubTask,
    context: SharedContext | None,
) -> SubAgentResult:
    """Execute a single subagent with isolated context (context protection).

    Each subagent gets its own clean context with only relevant information
    injected, preventing context pollution from other subtasks.
    """
    prompt_parts: list[str] = []
    if context:
        messages = context.get_messages(max_count=10)
        if messages:
            history = "\n".join(f"[{m.role}]: {m.text}" for m in messages if m.text)
            prompt_parts.append(f"Relevant context:\n{history}")
    prompt_parts.append(f"Task: {task.description}")

    system = agent.system_prompt if agent else "You are a helpful assistant. Complete the assigned task."
    tools = agent.tools if agent else []
    agent_model = (agent.model if agent and agent.model else model)

    request = ApiMessageRequest(
        model=agent_model,
        messages=[ConversationMessage.from_user_text("\n\n".join(prompt_parts))],
        system_prompt=system,
        max_tokens=4096,
        tools=tools,
    )

    collected_text = ""
    tokens = 0
    try:
        async for event in api_client.stream_message(request):
            if isinstance(event, ApiTextDeltaEvent):
                collected_text += event.text
            elif isinstance(event, ApiMessageCompleteEvent):
                if event.message.text:
                    collected_text = event.message.text
                tokens = event.usage.total_tokens
        return SubAgentResult(
            agent_name=agent.name if agent else "default",
            task=task,
            output=collected_text,
            status=TaskStatus.COMPLETED,
            tokens_used=tokens,
        )
    except Exception as exc:
        log.warning("Subagent %s failed: %s", agent.name if agent else "default", exc)
        return SubAgentResult(
            agent_name=agent.name if agent else "default",
            task=task,
            output="",
            status=TaskStatus.FAILED,
            error=str(exc),
        )


def resolve_execution_order(subtasks: list[SubTask]) -> list[list[SubTask]]:
    """Resolve subtask dependencies into execution layers (topological sort).

    Returns layers where tasks in the same layer can run in parallel,
    and each layer depends on all previous layers being complete.
    """
    if not subtasks:
        return []

    task_map = {t.task_id: t for t in subtasks}
    remaining = set(task_map.keys())
    completed: set[str] = set()
    layers: list[list[SubTask]] = []

    while remaining:
        # Find tasks whose dependencies are all completed
        ready = [
            tid for tid in remaining
            if all(dep in completed or dep not in task_map for dep in task_map[tid].dependencies)
        ]
        if not ready:
            # Circular dependency — put all remaining in one layer
            layers.append([task_map[tid] for tid in remaining])
            break
        layers.append([task_map[tid] for tid in ready])
        completed.update(ready)
        remaining -= set(ready)

    return layers


class Orchestrator:
    """Lead agent that spawns and manages specialized subagents.

    Implements the full orchestrator loop:
    1. Decompose task via TaskSplitter
    2. Resolve dependencies into parallel layers
    3. Execute layers (parallel within, sequential across)
    4. Verify each result via VerificationAgent
    5. Retry on failure (up to max_attempts)
    6. Merge and return results
    """

    def __init__(
        self,
        *,
        api_client: SupportsStreamingMessages,
        model: str,
        agents: dict[str, SpecializedAgent] | None = None,
        verification_agent: SpecializedAgent | None = None,
        max_attempts: int = 3,
    ) -> None:
        self._api_client = api_client
        self._model = model
        self._agents = agents or {}
        self._splitter = TaskSplitter(api_client=api_client, model=model)
        self._verification_agent = verification_agent
        self._max_attempts = max_attempts

    def register_agent(self, agent: SpecializedAgent) -> None:
        """Register a specialized agent for task routing."""
        self._agents[agent.name] = agent

    def _select_agent(self, task: SubTask) -> SpecializedAgent | None:
        """Select the best specialized agent for a task based on description."""
        desc_lower = task.description.lower()
        for name, agent in self._agents.items():
            if name.lower() in desc_lower:
                return agent
        return None

    async def run(
        self,
        user_request: str,
        context: SharedContext | None = None,
    ) -> str:
        """Execute the full orchestrator loop."""
        # 1. Decompose
        subtasks = await self._splitter.analyze_and_split(user_request, context)
        if not subtasks:
            # Single agent execution — no split needed
            result = await run_subagent(
                api_client=self._api_client,
                model=self._model,
                agent=None,
                task=SubTask(description=user_request),
                context=context,
            )
            return result.output

        # 2. Resolve execution order
        layers = resolve_execution_order(subtasks)

        # 3. Execute layers
        all_results: list[SubAgentResult] = []
        for layer in layers:
            layer_results = await asyncio.gather(*[
                self._execute_with_retry(task, context)
                for task in layer
            ])
            all_results.extend(layer_results)

            # Update shared context with completed results
            if context:
                for r in layer_results:
                    if r.status == TaskStatus.COMPLETED:
                        context.merge_result(r.agent_name, r.output)

        # 4. Merge results
        task_results = [
            SubTaskResult(
                task_id=r.task.task_id,
                status=r.status,
                output=r.output,
                error=r.error,
            )
            for r in all_results
        ]
        return await self._splitter.merge_results(subtasks, task_results)

    async def _execute_with_retry(
        self,
        task: SubTask,
        context: SharedContext | None,
    ) -> SubAgentResult:
        """Execute a subtask with verification and retry."""
        agent = self._select_agent(task)

        for attempt in range(self._max_attempts):
            result = await run_subagent(
                api_client=self._api_client,
                model=self._model,
                agent=agent,
                task=task,
                context=context,
            )

            if result.status == TaskStatus.FAILED:
                log.warning("Task %s failed (attempt %d): %s", task.task_id, attempt + 1, result.error)
                if attempt < self._max_attempts - 1:
                    continue
                return result

            # Verify if verification agent is configured
            if self._verification_agent:
                from openharness.coordinator.verification_agent import VerificationAgent
                verifier = VerificationAgent(
                    api_client=self._api_client,
                    model=self._verification_agent.model or self._model,
                    system_prompt=self._verification_agent.system_prompt,
                )
                verification = await verifier.verify(
                    task_description=task.description,
                    output=result.output,
                )
                if verification.passed:
                    return result
                log.warning(
                    "Task %s failed verification (attempt %d): %s",
                    task.task_id, attempt + 1, verification.issues,
                )
                if attempt < self._max_attempts - 1:
                    # Append failure info to task for retry
                    task = SubTask(
                        task_id=task.task_id,
                        description=f"{task.description}\n\nPrevious attempt failed verification: {'; '.join(verification.issues)}",
                        dependencies=task.dependencies,
                        context_refs=task.context_refs,
                        estimated_complexity=task.estimated_complexity,
                    )
                    continue
                result.status = TaskStatus.FAILED
                result.error = f"Verification failed: {'; '.join(verification.issues)}"
                return result

            return result

        return result  # type: ignore[possibly-undefined]
