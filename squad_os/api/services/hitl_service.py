from __future__ import annotations

from typing import Dict, List, Optional, Any

import aiosqlite

from squad_os.api.schemas import HITLInterruptDTO, HITLResolveRequest
from squad_os.core.events import EventType, InterruptEvent, get_bus
from squad_os.database.session import DB_PATH


class HITLService:
    async def get_pending_interrupts(self) -> List[HITLInterruptDTO]:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM mission_interrupts WHERE status = 'PENDING' ORDER BY id ASC"
            )
            rows = await cursor.fetchall()
            return [HITLInterruptDTO(
                id=r["id"], mission_id=r["mission_id"],
                task_idx=r.get("task_idx"),
                context=r.get("context"),
                error_message=r.get("error_message"),
                status=r["status"],
                created_at=r.get("created_at"),
            ) for r in rows]

    async def get_mission_interrupts(self, mission_id: int) -> List[HITLInterruptDTO]:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM mission_interrupts WHERE mission_id = ? ORDER BY id ASC",
                (mission_id,)
            )
            rows = await cursor.fetchall()
            return [HITLInterruptDTO(
                id=r["id"], mission_id=r["mission_id"],
                task_idx=r.get("task_idx"),
                context=r.get("context"),
                error_message=r.get("error_message"),
                status=r["status"],
                created_at=r.get("created_at"),
            ) for r in rows]

    async def resolve_interrupt(self, interrupt_id: int, guidance: str) -> bool:
        from squad_os.database.session import update_interrupt_guidance
        await update_interrupt_guidance(interrupt_id, guidance)
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM mission_interrupts WHERE id = ?", (interrupt_id,)
            )
            row = await cursor.fetchone()
            mission_id = row["mission_id"] if row else None
        if mission_id:
            await get_bus().publish(InterruptEvent(
                event_type=EventType.INTERRUPT_RESOLVED,
                mission_id=mission_id,
                interrupt_id=interrupt_id,
                resolved_guidance=guidance,
            ))
        return True

    async def get_pending_count(self) -> int:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM mission_interrupts WHERE status = 'PENDING'"
            )
            row = await cursor.fetchone()
            return row[0] if row else 0


hitl_service = HITLService()
