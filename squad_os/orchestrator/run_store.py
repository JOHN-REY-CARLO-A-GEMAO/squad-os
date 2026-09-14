"""RunStore — the storage seam for mission runs (staged commit 1).

The Manager (and, in the next stage, MissionRun) accesses run state —
task lifecycle, HITL interrupts, the blackboard, the event log, mission
snapshots, and mission status — exclusively through this port. SQL lives
in the adapter, never in the caller.

Two adapters justify the seam: SessionRunStore (production, delegating to
the squad_os.database.session functions) and, in the next stage, an
in-memory store for tests.

Behaviour note: every method mirrors the signature of the session
function it wraps, so call sites and test doubles keep working unchanged.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

import aiosqlite

from squad_os.database.session import (
    DB_PATH,
    append_conversation_event,
    create_interrupt,
    create_task,
    get_task,
    get_task_interrupt,
    update_blackboard,
    update_interrupt_guidance,
    update_mission,
    update_mission_snapshot,
    update_task,
)
from squad_os.database.session_missions import compute_mission_final_status


@runtime_checkable
class RunStore(Protocol):
    """The run-state interface: everything a mission run may persist or read.

    This is the only seam through which the orchestrator touches shared
    memory for run state. Prep-side concerns (mission creation, persona
    recruitment, follow-up conversation logging) stay on the session
    package directly.
    """

    async def create_task(self, mission_id: int, description: str, assigned_agent: str) -> int:
        """Insert a task row for a mission; returns the new task id."""
        ...

    async def update_task(self, task_id: int, **kwargs: Any) -> None:
        """Update mutable task columns (status, output_data, error, ...)."""
        ...

    async def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Fetch one task row (verification details, status, ...), or None."""
        ...

    async def get_mission_tasks(self, mission_id: int) -> List[Dict[str, Any]]:
        """Fetch a mission's task rows (description, status, output_data, assigned_agent), oldest first."""
        ...

    async def update_mission(self, mission_id: int, status: str) -> None:
        """Set a mission's status."""
        ...

    async def update_mission_uploaded_files(self, mission_id: int, uploaded_files_json: str) -> None:
        """Persist staged upload metadata onto the mission row."""
        ...

    async def create_interrupt(
        self,
        mission_id: int,
        task_idx: Optional[int] = None,
        context: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> int:
        """Raise a PENDING HITL interrupt; returns the new interrupt id."""
        ...

    async def get_task_interrupt(self, mission_id: int, task_idx: int) -> Optional[Dict[str, Any]]:
        """Latest interrupt for a mission+task, or None."""
        ...

    async def update_interrupt_guidance(self, interrupt_id: int, user_guidance: str) -> None:
        """Record human guidance and mark the interrupt RESOLVED."""
        ...

    async def update_blackboard(self, key: str, value: str) -> None:
        """Publish a value on the global blackboard."""
        ...

    async def append_conversation_event(
        self,
        conversation_id: int,
        event_namespace: str,
        event_type: str,
        payload: Dict[str, Any],
        parent_event_id: Optional[int] = None,
        mission_id: Optional[int] = None,
        payload_schema_version: int = 1,
    ) -> int:
        """Append to the event log; returns the new event id."""
        ...

    async def update_mission_snapshot(
        self,
        mission_id: int,
        status: str,
        progress: float,
        latest_thought: Optional[str] = None,
        next_action: Optional[str] = None,
        eta: int = 0,
        confidence: str = "HIGH",
        token_usage: int = 0,
        estimated_cost: float = 0.0,
    ) -> None:
        """Upsert the mission's progress snapshot."""
        ...

    def final_status(self, task_states: Dict[Any, str]) -> str:
        """Honest final mission status from per-task states."""
        ...


class SessionRunStore:
    """Production adapter: delegates run-state persistence to the
    squad_os.database.session functions against shared_memory.db."""

    async def create_task(self, mission_id: int, description: str, assigned_agent: str) -> int:
        return await create_task(mission_id, description, assigned_agent)

    async def update_task(self, task_id: int, **kwargs: Any) -> None:
        await update_task(task_id, **kwargs)

    async def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        return await get_task(task_id)

    async def get_mission_tasks(self, mission_id: int) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT description, status, output_data, assigned_agent FROM tasks WHERE mission_id = ? ORDER BY id",
                (mission_id,),
            )
            return [dict(r) for r in await cursor.fetchall()]

    async def update_mission(self, mission_id: int, status: str) -> None:
        await update_mission(mission_id, status)

    async def update_mission_uploaded_files(self, mission_id: int, uploaded_files_json: str) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE missions SET uploaded_files = ? WHERE id = ?",
                (uploaded_files_json, mission_id),
            )
            await db.commit()

    async def create_interrupt(
        self,
        mission_id: int,
        task_idx: Optional[int] = None,
        context: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> int:
        return await create_interrupt(
            mission_id=mission_id,
            task_idx=task_idx,
            context=context,
            error_message=error_message,
        )

    async def get_task_interrupt(self, mission_id: int, task_idx: int) -> Optional[Dict[str, Any]]:
        return await get_task_interrupt(mission_id, task_idx)

    async def update_interrupt_guidance(self, interrupt_id: int, user_guidance: str) -> None:
        await update_interrupt_guidance(interrupt_id, user_guidance)

    async def update_blackboard(self, key: str, value: str) -> None:
        await update_blackboard(key, value)

    async def append_conversation_event(
        self,
        conversation_id: int,
        event_namespace: str,
        event_type: str,
        payload: Dict[str, Any],
        parent_event_id: Optional[int] = None,
        mission_id: Optional[int] = None,
        payload_schema_version: int = 1,
    ) -> int:
        return await append_conversation_event(
            conversation_id=conversation_id,
            event_namespace=event_namespace,
            event_type=event_type,
            payload=payload,
            parent_event_id=parent_event_id,
            mission_id=mission_id,
            payload_schema_version=payload_schema_version,
        )

    async def update_mission_snapshot(
        self,
        mission_id: int,
        status: str,
        progress: float,
        latest_thought: Optional[str] = None,
        next_action: Optional[str] = None,
        eta: int = 0,
        confidence: str = "HIGH",
        token_usage: int = 0,
        estimated_cost: float = 0.0,
    ) -> None:
        await update_mission_snapshot(
            mission_id=mission_id,
            status=status,
            progress=progress,
            latest_thought=latest_thought,
            next_action=next_action,
            eta=eta,
            confidence=confidence,
            token_usage=token_usage,
            estimated_cost=estimated_cost,
        )

    def final_status(self, task_states: Dict[Any, str]) -> str:
        return compute_mission_final_status(task_states)
