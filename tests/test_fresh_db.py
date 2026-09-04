"""Fresh-database audit.

Guards against migration-order regressions (task verification columns must
exist on a brand-new database), verifies every table is created, seed data is
present, and that a full mission + scheduled dispatch works on the fresh DB.
"""
import json
import tempfile
from datetime import datetime

import aiosqlite
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from squad_os.database.session import (
    DB_PATH, init_db, create_mission, create_task, update_task,
    get_mission, add_to_queue, get_next_queued_mission, update_mission,
    get_all_personas, get_workspaces, get_conversations,
)
from squad_os.orchestrator.manager import Manager
from squad_os.tools.scheduler import ScheduleManager

EXPECTED_TABLES = {
    "missions", "tasks", "approvals", "blackboard", "schedules",
    "schedule_history", "mission_interrupts", "agent_personas",
    "store_packages", "installed_packages", "store_tools", "store_workflows",
    "workspaces", "conversations", "conversation_memories",
    "conversation_events", "mission_snapshots", "devices",
    "system_notifications",
}

EXPECTED_TASK_COLUMNS = {
    "id", "mission_id", "description", "assigned_agent", "status",
    "input_data", "output_data", "error", "prompt_tokens",
    "completion_tokens", "cost_usd", "execution_ms", "retry_count",
    "created_at", "verification_status", "verification_details",
}


def _text_response(content: str = "done"):
    return MagicMock(
        usage=MagicMock(prompt_tokens=1, completion_tokens=1, cost=0.0),
        choices=[MagicMock(message=MagicMock(
            model_dump=MagicMock(return_value={"content": content, "tool_calls": None})
        ))],
    )


def _workflow_json() -> str:
    return json.dumps({
        "tasks": [
            {"description": "fresh db task", "assigned_agent_role": "Maker", "depends_on": []},
        ],
        "suggested_parallelism": 1,
    })


async def _table_names() -> set:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        return {r[0] for r in await cursor.fetchall()}


@pytest.mark.asyncio
async def test_fresh_db_creates_all_tables_and_migrations(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.chdir(tmpdir)
    await init_db()

    tables = await _table_names()
    assert EXPECTED_TABLES <= tables, f"missing tables: {EXPECTED_TABLES - tables}"

    # Every migration column exists on the fresh DB (migration-order guard).
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("PRAGMA table_info(tasks)")
        task_cols = {r[1] for r in await cursor.fetchall()}
        cursor = await db.execute("PRAGMA table_info(missions)")
        mission_cols = {r[1] for r in await cursor.fetchall()}
    assert EXPECTED_TASK_COLUMNS <= task_cols, f"missing task columns: {EXPECTED_TASK_COLUMNS - task_cols}"
    assert {"uploaded_files", "workflow_json", "conversation_history"} <= mission_cols

    # Seed data: default workspace + conversation exist.
    workspaces = await get_workspaces()
    assert len(workspaces) >= 1
    assert len(await get_conversations(workspaces[0]["id"])) >= 1


@pytest.mark.asyncio
async def test_fresh_db_init_is_idempotent(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.chdir(tmpdir)
    await init_db()
    mid = await create_mission("keep me")
    await init_db()  # second init must not wipe or crash
    assert await get_mission(mid) is not None
    assert EXPECTED_TABLES <= await _table_names()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("PRAGMA table_info(tasks)")
        cols = {r[1] for r in await cursor.fetchall()}
    assert "verification_status" in cols


@pytest.mark.asyncio
async def test_fresh_db_mission_and_task_creation(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.chdir(tmpdir)
    await init_db()

    mid = await create_mission("lifecycle goal")
    task_id = await create_task(mid, "write code", "Maker")
    # update_task with the migrated columns must work on a fresh DB.
    await update_task(task_id, status="COMPLETED",
                      verification_status="PASSED",
                      verification_details=json.dumps({"passed": True}))
    await update_mission(mid, "COMPLETED")

    assert (await get_mission(mid))["status"] == "COMPLETED"

    # Personas table is usable.
    assert await get_all_personas() == []


@pytest.mark.asyncio
async def test_fresh_db_full_queued_mission_dispatch(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.chdir(tmpdir)
    await init_db()

    await add_to_queue("fresh queued goal")
    queued = await get_next_queued_mission()
    assert queued is not None
    mid = queued["id"]
    await update_mission(mid, "IN_PROGRESS")

    manager = Manager(tool_inventory=[], model_name="gpt-4o-mini", verification_enabled=False)
    with patch("litellm.acompletion", AsyncMock(return_value=_text_response("done"))):
        outcome = await manager.run_mission("fresh queued goal", None, _workflow_json(), mission_id=mid)

    assert outcome == "COMPLETED"
    assert (await get_mission(mid))["status"] == "COMPLETED"
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM tasks WHERE mission_id = ?", (mid,))
        assert (await cursor.fetchone())[0] == 1
    assert await get_next_queued_mission() is None


@pytest.mark.asyncio
async def test_fresh_db_scheduled_mission_dispatch(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.chdir(tmpdir)
    await init_db()

    # Schedule a one-time run due immediately (worker's atomic claim path).
    sid = await ScheduleManager.add_schedule("fresh scheduled goal", "once", datetime.now().isoformat())
    claimed = await ScheduleManager.claim_due_schedules()
    assert [s["id"] for s in claimed] == [sid]

    mission_id = await create_mission("fresh scheduled goal")
    manager = Manager(tool_inventory=[], model_name="gpt-4o-mini", verification_enabled=False)
    with patch("litellm.acompletion", AsyncMock(return_value=_text_response("done"))):
        outcome = await manager.run_mission("fresh scheduled goal", None, _workflow_json(), mission_id=mission_id)
    await ScheduleManager.update_schedule_after_run(sid, mission_id, outcome)

    assert outcome == "COMPLETED"
    assert (await get_mission(mission_id))["status"] == "COMPLETED"
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM schedules WHERE id = ?", (sid,))
        sched = dict(await cursor.fetchone())
        cursor = await db.execute(
            "SELECT status, mission_id FROM schedule_history WHERE schedule_id = ?", (sid,)
        )
        history = [tuple(r) for r in await cursor.fetchall()]
    assert sched["status"] == "COMPLETED"
    assert sched["mission_id"] == mission_id
    assert history == [("COMPLETED", mission_id)]
    assert await ScheduleManager.claim_due_schedules() == []
