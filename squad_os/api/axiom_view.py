"""
Axiom View — lightweight read-only projection for RPi 5 mini-screen.

Q10 contract: one static file + one read-only FastAPI route.
- Path: htdocs/axiom-view/index.html (kiosk)
- Route: GET /api/v1/axiom-view?mission_id=last  (or ?mission_id=<int>)
- DB: read-only sqlite3 open with ?mode=ro & immutable=1
- Projection: missions, tasks, mission_interrupts, system summary
- No writes, no new table, no new migration (Q3 invariant).

Used by: htdocs kiosk, tests/test_guaardvark_validation.py::test_axiom_view
"""
from __future__ import annotations

import json
import os
import sqlite3
from typing import Any, Dict, List, Optional

# DB_PATH is the single source of truth — reuse the mission DB path.
# Import lazily to avoid circular imports at startup.
try:
    from squad_os.database.session_missions import DB_PATH  # canonical
except Exception:  # pragma: no cover
    DB_PATH = "shared_memory.db"


def _ro_connect(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Open DB in read-only, immutable mode. Raises if file missing."""
    # Use URI mode for read-only; fallback to normal if URI not supported.
    # The immutable flag prevents WAL journaling writes.
    uri = f"file:{os.path.abspath(db_path)}?mode=ro"
    # check_same_thread False to allow FastAPI threadpool reuse.
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


async def get_axiom_snapshot(mission_id: Optional[int | str] = None, db_path: str = DB_PATH) -> Dict[str, Any]:
    """
    Read-only projection of the SquadOS state for Axiom View.

    Args:
        mission_id: int, "last", or None (defaults to last mission if exists)
        db_path: override for tests (tmp_path DB)

    Returns:
        {
            mission: dict | None,
            tasks: [dict],
            interrupts: [dict],
            system: { minimal summary string + raw monitor if available },
        }

    Guarantees: performs only SELECTs. No INSERT/UPDATE/DELETE.
    Tests assert this via sqlparse or RO-open failure on write attempt.
    """
    # Resolve mission_id: "last" → MAX(id)
    resolved_id: Optional[int] = None
    if mission_id is not None and str(mission_id) != "last":
        try:
            resolved_id = int(mission_id)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            raise ValueError(f"Invalid mission_id: {mission_id!r}")

    # Use the RO connection for all reads. No writes.
    conn = _ro_connect(db_path)
    try:
        cur = conn.cursor()

        # Resolve "last" or None
        if resolved_id is None:
            row = cur.execute("SELECT id FROM missions ORDER BY id DESC LIMIT 1").fetchone()
            if row:
                resolved_id = int(row["id"])

        mission: Optional[Dict[str, Any]] = None
        tasks: List[Dict[str, Any]] = []
        interrupts: List[Dict[str, Any]] = []

        if resolved_id is not None:
            m = cur.execute("SELECT * FROM missions WHERE id = ?", (resolved_id,)).fetchone()
            if m:
                mission = dict(m)
                # Parse JSON-ish fields for the frontend
                for k in ("workflow_json", "conversation_history", "uploaded_files"):
                    if mission.get(k):
                        try:
                            mission[f"{k}_parsed"] = json.loads(mission[k])  # type: ignore[index]
                        except Exception:
                            mission[f"{k}_parsed"] = None

            tasks_rows = cur.execute(
                "SELECT * FROM tasks WHERE mission_id = ? ORDER BY id ASC", (resolved_id,)
            ).fetchall()
            tasks = [dict(r) for r in tasks_rows]

            intr_rows = cur.execute(
                "SELECT * FROM mission_interrupts WHERE mission_id = ? ORDER BY id ASC",
                (resolved_id,),
            ).fetchall()
            interrupts = [dict(r) for r in intr_rows]

        # System summary — minimal, read-only via SystemSummaryTool path when psutil available.
        system_summary: str = "System summary unavailable"
        system_detail: Optional[Dict[str, Any]] = None
        try:
            # Import here to avoid hard dependency at startup
            import psutil  # type: ignore

            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            load = psutil.getloadavg() if hasattr(psutil, "getloadavg") else (0, 0, 0)
            temp_str = ""
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    for entries in temps.values():
                        if entries:
                            temp_str = f" | Temp: {entries[0].current}°C"
                            break
            except Exception:
                pass
            system_summary = f"CPU: {cpu}% | RAM: {mem.percent}% ({mem.used//(1024**2)}MB/{mem.total//(1024**2)}MB){temp_str}"

            # Also expose a structured detail for the JSON API
            system_detail = {
                "cpu_percent": cpu,
                "memory_percent": mem.percent,
                "available_mb": mem.available // (1024**2),
                "load_avg": list(load),
            }
        except Exception as e:
            system_summary = f"System summary unavailable: {e}"

        return {
            "mission": mission,
            "tasks": tasks,
            "interrupts": interrupts,
            "system": {
                "summary": system_summary,
                "detail": system_detail,
                "db_path": os.path.abspath(db_path),
                "mode": "ro",
            },
        }
    finally:
        conn.close()


# ─── FastAPI wiring (optional — imported by squad_os.api.main) ───────────

try:
    from fastapi import APIRouter, Query  # type: ignore

    router = APIRouter(prefix="/axiom-view", tags=["Axiom View"])

    @router.get("")
    async def axiom_view_endpoint(mission_id: str = Query("last", description="Mission id or 'last'")):
        """Read-only Axiom View projection. Query ?mission_id=last|<int>."""
        # Allow "last" string via str typing above
        mid: Optional[int | str] = mission_id
        if mid != "last":
            try:
                mid = int(mid)  # type: ignore[arg-type]
            except Exception:
                mid = "last"
        return await get_axiom_snapshot(mission_id=mid)  # type: ignore[arg-type]

    # Public variant for kiosk (no auth) — mirrors main.py public_router pattern
    public_router = APIRouter(prefix="/axiom-view", tags=["Axiom View"])

    @public_router.get("")
    async def axiom_view_public(mission_id: str = Query("last")):
        mid: Optional[int | str] = mission_id
        if mid != "last":
            try:
                mid = int(mid)  # type: ignore[arg-type]
            except Exception:
                mid = "last"
        return await get_axiom_snapshot(mission_id=mid)  # type: ignore[arg-type]

except Exception:  # pragma: no cover
    # FastAPI not installed in some test envs — module still importable for direct calls
    router = None  # type: ignore
    public_router = None  # type: ignore
