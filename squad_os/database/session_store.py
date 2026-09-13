"""Store / schedules / devices persistence.

Split from session.py (PR4). Move-only: no logic changes.
Table DDL lives in session_missions.init_db; this module owns the
device CRUD. (No schedule/store CRUD existed in session.py — services
run their own SQL.)
"""

import aiosqlite
from typing import Any, Dict, List, Optional

from squad_os.database.session_missions import DB_PATH

async def register_device(
    push_token: str,
    platform: str,
    device_model: Optional[str] = None,
    user_id: str = "default_user"
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO devices (push_token, platform, device_model, user_id, is_active, last_seen_at)
            VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(push_token) DO UPDATE SET
                is_active = 1,
                last_seen_at = CURRENT_TIMESTAMP
            """,
            (push_token, platform, device_model, user_id)
        )
        await db.commit()
        cursor = await db.execute("SELECT id FROM devices WHERE push_token = ?", (push_token,))
        row = await cursor.fetchone()
        return row[0] if row else 0

async def get_active_devices() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM devices WHERE is_active = 1") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def revoke_device(device_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE devices SET is_active = 0 WHERE id = ?", (device_id,))
        await db.commit()
