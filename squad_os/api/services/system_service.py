from __future__ import annotations

import os
import time
from typing import Optional

import aiosqlite

from squad_os.api.schemas import SystemHealthDTO, SystemMetricsDTO
from squad_os.database.session import DB_PATH


_start_time = time.time()


class SystemService:
    async def get_health(self) -> SystemHealthDTO:
        active = 0
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM missions WHERE status IN ('IN_PROGRESS', 'QUEUED')"
                )
                row = await cursor.fetchone()
                active = row[0] if row else 0
        except Exception:
            pass
        return SystemHealthDTO(
            status="online",
            worker_active=True,
            uptime_seconds=time.time() - _start_time,
            active_missions=active,
            agents_online=len(os.environ.get("SQUAD_OS_MODEL", "default").split(",")),
        )

    async def get_metrics(self) -> SystemMetricsDTO:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            m_total = m_completed = m_failed = 0
            t_total = t_completed = t_failed = 0
            tokens_prompt = tokens_completion = 0
            cost = 0.0

            cursor = await db.execute("SELECT COUNT(*) as c FROM missions")
            row = await cursor.fetchone()
            m_total = row["c"] if row else 0

            cursor = await db.execute("SELECT COUNT(*) as c FROM missions WHERE status = 'COMPLETED'")
            row = await cursor.fetchone()
            m_completed = row["c"] if row else 0

            cursor = await db.execute("SELECT COUNT(*) as c FROM missions WHERE status = 'FAILED'")
            row = await cursor.fetchone()
            m_failed = row["c"] if row else 0

            cursor = await db.execute("SELECT COUNT(*) as c FROM tasks")
            row = await cursor.fetchone()
            t_total = row["c"] if row else 0

            cursor = await db.execute("SELECT COUNT(*) as c FROM tasks WHERE status = 'COMPLETED'")
            row = await cursor.fetchone()
            t_completed = row["c"] if row else 0

            cursor = await db.execute("SELECT COUNT(*) as c FROM tasks WHERE status = 'FAILED'")
            row = await cursor.fetchone()
            t_failed = row["c"] if row else 0

            cursor = await db.execute("SELECT COALESCE(SUM(prompt_tokens), 0) as v FROM tasks")
            row = await cursor.fetchone()
            tokens_prompt = row["v"] if row else 0

            cursor = await db.execute("SELECT COALESCE(SUM(completion_tokens), 0) as v FROM tasks")
            row = await cursor.fetchone()
            tokens_completion = row["v"] if row else 0

            cursor = await db.execute("SELECT COALESCE(SUM(cost_usd), 0.0) as v FROM tasks")
            row = await cursor.fetchone()
            cost = row["v"] if row else 0.0

            return SystemMetricsDTO(
                missions_total=m_total,
                missions_completed=m_completed,
                missions_failed=m_failed,
                tasks_total=t_total,
                tasks_completed=t_completed,
                tasks_failed=t_failed,
                total_prompt_tokens=tokens_prompt,
                total_completion_tokens=tokens_completion,
                total_cost_usd=cost,
            )


system_service = SystemService()
