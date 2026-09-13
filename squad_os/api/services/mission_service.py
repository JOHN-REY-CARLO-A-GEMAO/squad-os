from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiosqlite

from squad_os.api.schemas import (
    DAGEdge, DAGLayout, DAGNode, MissionDTO, MissionSummaryDTO,
    MissionTimelineEntry, TaskDTO,
)
from squad_os.core.events import (
    EventType, MissionEvent, PlanEvent, TaskEvent, get_bus,
)
from squad_os.database.session import DB_PATH


class MissionService:
    async def list_missions(self, status: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[MissionSummaryDTO]:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            conditions = ""
            params: List[Any] = []
            if status:
                conditions = "WHERE m.status = ?"
                params.append(status.upper())
            cursor = await db.execute(f"""
                SELECT m.*,
                    (SELECT COUNT(*) FROM tasks t WHERE t.mission_id = m.id) as task_count,
                    (SELECT COUNT(*) FROM tasks t WHERE t.mission_id = m.id AND t.status = 'COMPLETED') as completed_count,
                    (SELECT COUNT(*) FROM tasks t WHERE t.mission_id = m.id AND t.status = 'FAILED') as failed_count
                FROM missions m
                {conditions}
                ORDER BY m.id DESC
                LIMIT ? OFFSET ?
            """, params + [limit, offset])
            rows = await cursor.fetchall()
            return [MissionSummaryDTO(
                id=r["id"],
                goal=r["goal"][:120] + ("..." if len(r["goal"]) > 120 else ""),
                status=r["status"],
                task_count=r["task_count"],
                completed_count=r["completed_count"],
                failed_count=r["failed_count"],
                created_at=r["created_at"],
            ) for r in rows]

    async def get_mission(self, mission_id: int) -> Optional[MissionDTO]:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM missions WHERE id = ?", (mission_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            return MissionDTO(
                id=row["id"], goal=row["goal"], status=row["status"],
                uploaded_files=row["uploaded_files"],
                workflow_json=row["workflow_json"],
                conversation_history=row["conversation_history"] or "[]",
                created_at=row["created_at"],
            )

    async def get_mission_tasks(self, mission_id: int) -> List[TaskDTO]:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM tasks WHERE mission_id = ? ORDER BY id ASC", (mission_id,)
            )
            rows = await cursor.fetchall()
            return [TaskDTO(
                id=r["id"], mission_id=r["mission_id"],
                description=r["description"],
                assigned_agent=r["assigned_agent"],
                status=r["status"],
                input_data=r["input_data"],
                output_data=r["output_data"],
                error=r["error"],
                prompt_tokens=r["prompt_tokens"] or 0,
                completion_tokens=r["completion_tokens"] or 0,
                cost_usd=r["cost_usd"] or 0.0,
                execution_ms=r["execution_ms"] or 0,
                retry_count=r["retry_count"] or 0,
                verification_status=r["verification_status"],
                verification_details=r["verification_details"],
                created_at=r["created_at"],
            ) for r in rows]

    async def get_mission_timeline(self, mission_id: int) -> List[MissionTimelineEntry]:
        entries = []
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            mission = await db.execute("SELECT * FROM missions WHERE id = ?", (mission_id,))
            row = await mission.fetchone()
            if not row:
                return entries
            entries.append(MissionTimelineEntry(
                event_type="mission.created",
                timestamp=row["created_at"],
                detail="Mission created"
            ))
            entries.append(MissionTimelineEntry(
                event_type=f"mission.{row['status'].lower()}",
                timestamp=row["created_at"],
                detail=f"Mission {row['status'].lower()}"
            ))
            cursor = await db.execute(
                "SELECT * FROM tasks WHERE mission_id = ? ORDER BY id ASC", (mission_id,)
            )
            tasks = await cursor.fetchall()
            for t in tasks:
                entries.append(MissionTimelineEntry(
                    event_type=f"task.{t['status'].lower()}",
                    timestamp=t["created_at"],
                    detail=f"Task: {t['description'][:80]}"
                ))
        return entries

    async def get_mission_dag(self, mission_id: int) -> Optional[DAGLayout]:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            mission = await db.execute("SELECT workflow_json FROM missions WHERE id = ?", (mission_id,))
            row = await mission.fetchone()
            if not row:
                return None
            workflow_json = row["workflow_json"]
            cursor = await db.execute(
                "SELECT * FROM tasks WHERE mission_id = ? ORDER BY id ASC", (mission_id,)
            )
            tasks = await cursor.fetchall()
            if not tasks:
                return None

            nodes = []
            edges = []
            for i, t in enumerate(tasks):
                nodes.append(DAGNode(
                    id=f"task_{i}",
                    title=t["description"][:60],
                    status=t["status"],
                    agent_role=t["assigned_agent"],
                    x=(i % 3) * 250 + 50,
                    y=(i // 3) * 180 + 50,
                ))
            if workflow_json:
                try:
                    wf = json.loads(workflow_json)
                    for i, wt in enumerate(wf.get("tasks", [])):
                        for dep in wt.get("depends_on", []):
                            if dep < len(tasks):
                                edges.append(DAGEdge(from_node=f"task_{dep}", to_node=f"task_{i}"))
                except (json.JSONDecodeError, IndexError):
                    pass
            if not edges:
                for i in range(1, len(tasks)):
                    edges.append(DAGEdge(from_node=f"task_{i-1}", to_node=f"task_{i}"))
            return DAGLayout(nodes=nodes, edges=edges)

    async def pause_mission(self, mission_id: int) -> bool:
        from squad_os.database.session import set_mission_status
        await set_mission_status(mission_id, "PAUSED")
        await get_bus().publish(MissionEvent(
            event_type=EventType.MISSION_PAUSED,
            mission_id=mission_id,
            status="PAUSED",
        ))
        return True

    async def resume_mission(self, mission_id: int) -> bool:
        from squad_os.database.session import set_mission_status
        await set_mission_status(mission_id, "QUEUED")
        await get_bus().publish(MissionEvent(
            event_type=EventType.MISSION_RESUMED,
            mission_id=mission_id,
            status="QUEUED",
        ))
        return True

    async def cancel_mission(self, mission_id: int) -> bool:
        from squad_os.database.session import set_mission_status
        await set_mission_status(mission_id, "CANCELLED")
        await get_bus().publish(MissionEvent(
            event_type=EventType.MISSION_CANCELLED,
            mission_id=mission_id,
            status="CANCELLED",
        ))
        return True

    async def queue_mission(self, goal: str, uploaded_files_json: Optional[str] = None) -> int:
        from squad_os.database.session import add_to_queue
        await add_to_queue(goal, uploaded_files_json)
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT MAX(id) FROM missions")
            row = await cursor.fetchone()
            mission_id = row[0] if row else 0
        await get_bus().publish(MissionEvent(
            event_type=EventType.MISSION_CREATED,
            mission_id=mission_id,
            goal=goal,
            status="QUEUED",
        ))
        return mission_id


mission_service = MissionService()
