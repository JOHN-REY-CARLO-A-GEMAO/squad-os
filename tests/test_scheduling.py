"""Regression tests for the scheduling feature and the run_mission contract.

Covers:
- Manager.run_mission(mission_id=...) reuses the caller's mission row instead of
  inserting a duplicate, sets the mission's final status, and returns the outcome
  (contract that worker.py / start_worker.py dispatch on).
- ScheduleManager.update_schedule_after_run: once-type schedules complete after
  firing (never refire), recurring schedules stay ACTIVE with an advanced
  next_run, and the real mission id is recorded in history.
"""
import json
import tempfile
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import aiosqlite
import pytest

from squad_os.database.session import DB_PATH, init_db, create_mission, get_mission
from squad_os.orchestrator.manager import Manager
from squad_os.tools.scheduler import ScheduleManager


def _text_response(content: str = "done"):
    """Acompletion response with a plain text answer (no tool calls)."""
    return MagicMock(
        usage=MagicMock(prompt_tokens=1, completion_tokens=1, cost=0.0),
        choices=[MagicMock(message=MagicMock(
            model_dump=MagicMock(return_value={"content": content, "tool_calls": None})
        ))],
    )


def _workflow_json() -> str:
    return json.dumps({
        "tasks": [
            {"description": "produce a summary", "assigned_agent_role": "Maker", "depends_on": []},
        ],
        "suggested_parallelism": 1,
    })


@pytest.mark.asyncio
async def test_run_mission_reuses_provided_mission_id(monkeypatch):
    # Isolate DB + branch workspace in a temp dir (DB_PATH is cwd-relative).
    tmpdir = tempfile.mkdtemp()
    monkeypatch.chdir(tmpdir)
    await init_db()

    mid = await create_mission("scheduled goal")  # status IN_PROGRESS by default
    manager = Manager(tool_inventory=[], model_name="gpt-4o-mini", verification_enabled=False)

    with patch("litellm.acompletion", AsyncMock(return_value=_text_response("summary written"))):
        outcome = await manager.run_mission("scheduled goal", None, _workflow_json(), mission_id=mid)

    assert outcome == "COMPLETED"
    row = await get_mission(mid)
    assert row is not None
    assert row["status"] == "COMPLETED"

    # No duplicate mission row was created for the same goal.
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM missions WHERE goal = ?", ("scheduled goal",))
        assert (await cursor.fetchone())[0] == 1
        # The task was attached to the caller's mission id.
        cursor = await db.execute("SELECT COUNT(*) FROM tasks WHERE mission_id = ?", (mid,))
        assert (await cursor.fetchone())[0] == 1


@pytest.mark.asyncio
async def test_run_mission_returns_failed_when_planning_fails(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.chdir(tmpdir)
    await init_db()

    manager = Manager(tool_inventory=[], model_name="gpt-4o-mini", verification_enabled=False)

    # recruit_squad/plan_mission call litellm.acompletion; force a crash mid-planning.
    with patch("litellm.acompletion", AsyncMock(side_effect=RuntimeError("llm down"))):
        outcome = await manager.run_mission("flaky goal")

    assert outcome == "FAILED"
    # run_mission created its own mission row and must have marked it FAILED
    # (not left IN_PROGRESS), so the caller never mis-completes it.
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id, status FROM missions WHERE goal = ?", ("flaky goal",))
        rows = await cursor.fetchall()
    assert len(rows) == 1
    assert rows[0][1] == "FAILED"


@pytest.mark.asyncio
async def test_once_schedule_completes_after_run_and_never_refires(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.chdir(tmpdir)
    await init_db()

    sid = await ScheduleManager.add_schedule(
        "once goal", "once", (datetime.now() + timedelta(days=1)).isoformat()
    )
    # Simulate that the scheduled time arrived.
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE schedules SET next_run = ? WHERE id = ?",
            (datetime.now().isoformat(), sid),
        )
        await db.commit()

    due = await ScheduleManager.get_due_schedules()
    assert [s["id"] for s in due] == [sid]

    await ScheduleManager.update_schedule_after_run(sid, 42, "COMPLETED")

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM schedules WHERE id = ?", (sid,))
        row = dict(await cursor.fetchone())
        cursor = await db.execute(
            "SELECT status FROM schedule_history WHERE schedule_id = ? AND mission_id = 42",
            (sid,),
        )
        history = await cursor.fetchall()

    assert row["status"] == "COMPLETED", "once schedule must not stay due"
    assert row["mission_id"] == 42
    assert [h[0] for h in history] == ["COMPLETED"]
    # get_due_schedules only returns ACTIVE rows — no refire.
    assert await ScheduleManager.get_due_schedules() == []


@pytest.mark.asyncio
async def test_interval_schedule_stays_active_and_advances_next_run(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.chdir(tmpdir)
    await init_db()

    sid = await ScheduleManager.add_schedule("interval goal", "interval", "60")
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT next_run FROM schedules WHERE id = ?", (sid,))
        original_next_run = (await cursor.fetchone())[0]

    await ScheduleManager.update_schedule_after_run(sid, 7, "COMPLETED")

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM schedules WHERE id = ?", (sid,))
        row = dict(await cursor.fetchone())

    assert row["status"] == "ACTIVE", "recurring schedule must remain active"
    assert row["mission_id"] == 7
    assert row["next_run"] is not None
    assert row["next_run"] > original_next_run, "next_run must advance past previous run"
    assert row["next_run"] > datetime.now().isoformat()
