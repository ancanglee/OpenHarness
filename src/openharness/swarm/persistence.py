"""Agent state persistence for cross-session save/restore.

Stores agent state as JSON files under ``~/.openharness/agents/``.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_DEFAULT_DIR = Path.home() / ".openharness" / "agents"


@dataclass
class AgentState:
    """Serialisable snapshot of an agent's lifecycle state."""

    agent_id: str
    name: str
    agent_type: str = "general-purpose"
    status: str = "active"  # active | paused | stopped | completed | failed
    created_at: str = ""
    paused_at: str | None = None
    messages_summary: str = ""
    tool_use_count: int = 0
    total_tokens: int = 0
    team: str | None = None
    backend: str = "in_process"
    config: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentState":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


@dataclass(frozen=True)
class AgentSummary:
    """Lightweight summary for listing persisted agents."""

    agent_id: str
    name: str
    agent_type: str
    status: str
    created_at: str
    paused_at: str | None
    token_count: int


def _safe_filename(agent_id: str) -> str:
    """Convert an agent_id to a safe filename."""
    return agent_id.replace("@", "_at_").replace("/", "_") + ".json"


class AgentPersistence:
    """File-system backed agent state persistence."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or _DEFAULT_DIR
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, agent_id: str) -> Path:
        return self._dir / _safe_filename(agent_id)

    async def save_state(self, agent_id: str, state: AgentState) -> None:
        """Persist *state* to a JSON file."""
        import asyncio

        path = self._path(agent_id)
        payload = json.dumps(state.to_dict(), indent=2, ensure_ascii=False)

        def _write() -> None:
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(payload, encoding="utf-8")
            os.replace(tmp, path)
            os.chmod(path, 0o600)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _write)
        log.debug("Saved agent state: %s → %s", agent_id, path)

    async def load_state(self, agent_id: str) -> AgentState | None:
        """Load agent state from disk. Returns *None* if not found."""
        import asyncio

        path = self._path(agent_id)

        def _read() -> AgentState | None:
            if not path.exists():
                return None
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return AgentState.from_dict(data)
            except (json.JSONDecodeError, KeyError, TypeError):
                log.warning("Corrupted agent state file: %s", path)
                return None

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _read)

    async def list_agents(self) -> list[AgentSummary]:
        """List all persisted agents."""
        import asyncio

        def _scan() -> list[AgentSummary]:
            results: list[AgentSummary] = []
            for path in sorted(self._dir.glob("*.json")):
                if path.name.endswith(".tmp"):
                    continue
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    results.append(AgentSummary(
                        agent_id=data.get("agent_id", ""),
                        name=data.get("name", ""),
                        agent_type=data.get("agent_type", ""),
                        status=data.get("status", ""),
                        created_at=data.get("created_at", ""),
                        paused_at=data.get("paused_at"),
                        token_count=data.get("total_tokens", 0),
                    ))
                except (json.JSONDecodeError, KeyError):
                    continue
            return results

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _scan)

    async def delete_state(self, agent_id: str) -> None:
        """Remove a persisted agent state file."""
        path = self._path(agent_id)
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

    async def cleanup_expired(self, max_age_hours: int = 72) -> int:
        """Remove state files older than *max_age_hours*. Returns count removed."""
        import asyncio

        now = time.time()
        cutoff = now - max_age_hours * 3600
        paused_cutoff = now - max_age_hours * 2 * 3600  # 2x for paused

        def _cleanup() -> int:
            removed = 0
            for path in list(self._dir.glob("*.json")):
                if path.name.endswith(".tmp"):
                    continue
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    status = data.get("status", "")
                    mtime = path.stat().st_mtime

                    should_remove = False
                    if status in ("completed", "failed") and mtime < cutoff:
                        should_remove = True
                    elif status == "paused" and mtime < paused_cutoff:
                        should_remove = True

                    if should_remove:
                        path.unlink()
                        removed += 1
                except (json.JSONDecodeError, OSError):
                    continue
            return removed

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _cleanup)
