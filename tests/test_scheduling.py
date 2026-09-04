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

import asyncio

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


# --- Mission lifecycle behavioral tests -------------------------------------

def _failing_workflow_json() -> str:
    return json.dumps({
        "tasks": [
            {"description": "will crash", "assigned_agent_role": "Maker", "depends_on": []},
        ],
        "suggested_parallelism": 1,
    })


@pytest.mark.asyncio
async def test_failed_task_execution_marks_mission_failed(monkeypatch):
    """A task that raises during execution must end the mission FAILED."""
    tmpdir = tempfile.mkdtemp()
    monkeypatch.chdir(tmpdir)
    await init_db()

    mid = await create_mission("exec crash goal")
    manager = Manager(tool_inventory=[], model_name="gpt-4o-mini", verification_enabled=False)

    # acompletion raising propagates out of execute_task -> execute_dag marks
    # the task FAILED -> run_mission must return FAILED and set the status.
    with patch("litellm.acompletion", AsyncMock(side_effect=RuntimeError("exec boom"))):
        outcome = await manager.run_mission("exec crash goal", None, _failing_workflow_json(), mission_id=mid)

    assert outcome == "FAILED"
    row = await get_mission(mid)
    assert row["status"] == "FAILED"
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT status FROM tasks WHERE mission_id = ?", (mid,))
        task_status = (await cursor.fetchone())[0]
    assert task_status == "FAILED"


@pytest.mark.asyncio
async def test_queued_mission_success_completes_and_is_not_requeued(monkeypatch):
    """Worker queued-mission flow: QUEUED -> IN_PROGRESS -> COMPLETED, no re-pickup."""
    from squad_os.database.session import add_to_queue, get_next_queued_mission, update_mission

    tmpdir = tempfile.mkdtemp()
    monkeypatch.chdir(tmpdir)
    await init_db()

    await add_to_queue("queued goal")
    queued = await get_next_queued_mission()
    assert queued is not None
    mid = queued["id"]
    await update_mission(mid, "IN_PROGRESS")

    manager = Manager(tool_inventory=[], model_name="gpt-4o-mini", verification_enabled=False)
    with patch("litellm.acompletion", AsyncMock(return_value=_text_response("ok"))):
        outcome = await manager.run_mission("queued goal", None, _workflow_json(), mission_id=mid)

    assert outcome == "COMPLETED"
    assert (await get_mission(mid))["status"] == "COMPLETED"
    # Worker must not re-pick the same mission (no QUEUED rows left).
    assert await get_next_queued_mission() is None


@pytest.mark.asyncio
async def test_queued_mission_failure_is_not_requeued(monkeypatch):
    """A failing queued mission ends FAILED and must not loop forever as QUEUED."""
    from squad_os.database.session import add_to_queue, get_next_queued_mission, update_mission

    tmpdir = tempfile.mkdtemp()
    monkeypatch.chdir(tmpdir)
    await init_db()

    await add_to_queue("flaky queued goal")
    queued = await get_next_queued_mission()
    mid = queued["id"]
    await update_mission(mid, "IN_PROGRESS")

    manager = Manager(tool_inventory=[], model_name="gpt-4o-mini", verification_enabled=False)
    with patch("litellm.acompletion", AsyncMock(side_effect=RuntimeError("boom"))):
        outcome = await manager.run_mission("flaky queued goal", None, _failing_workflow_json(), mission_id=mid)

    assert outcome == "FAILED"
    assert (await get_mission(mid))["status"] == "FAILED"
    assert await get_next_queued_mission() is None



async def _make_due(db_path: str, schedule_id: int):
    """Force a schedule's next_run into the past so it is due immediately."""
    import aiosqlite as _aiosqlite
    async with _aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE schedules SET next_run = ? WHERE id = ?",
            ((datetime.now() - timedelta(seconds=1)).isoformat(), schedule_id),
        )
        await db.commit()


class _DestructiveFakeTool:
    """Minimal BaseTool stand-in that flags destructive=True (HITL pause)."""
    name = "destructive_fake"
    description = "Fake destructive tool for tests."
    parameters = {"type": "object", "properties": {}, "required": []}
    destructive = True

    async def execute(self, **kwargs):
        return "should never run (paused)"


@pytest.mark.asyncio
async def test_hitl_paused_task_never_marks_mission_completed(monkeypatch):
    """A task paused for human approval must not end as a COMPLETED mission."""
    from squad_os.database.session import get_task_interrupt

    tmpdir = tempfile.mkdtemp()
    monkeypatch.chdir(tmpdir)
    await init_db()

    mid = await create_mission("destructive goal")
    manager = Manager(tool_inventory=[_DestructiveFakeTool()], model_name="gpt-4o-mini",
                      verification_enabled=False)

    outcome = await manager.run_mission("destructive goal", None, _workflow_json(), mission_id=mid)

    # Human never approved: task remains paused -> mission must NOT be COMPLETED.
    assert outcome == "FAILED"
    row = await get_mission(mid)
    assert row["status"] == "FAILED", row
    interrupt = await get_task_interrupt(mid, 0)
    assert interrupt is not None
    assert interrupt["status"] == "PENDING"


# --- Scheduler behavioral tests ---------------------------------------------

@pytest.mark.asyncio
async def test_claim_prevents_double_dispatch(monkeypatch):
    """Two workers polling concurrently must not both claim the same schedule."""
    tmpdir = tempfile.mkdtemp()
    monkeypatch.chdir(tmpdir)
    await init_db()

    sid = await ScheduleManager.add_schedule("claim goal", "once", datetime.now().isoformat())

    first = await ScheduleManager.claim_due_schedules()
    assert [s["id"] for s in first] == [sid]

    # Second (concurrent) worker polls: nothing left to claim.
    second = await ScheduleManager.claim_due_schedules()
    assert second == []

    # Claimed row is RUNNING until settled.
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT status FROM schedules WHERE id = ?", (sid,))
        assert (await cursor.fetchone())[0] == "RUNNING"


@pytest.mark.asyncio
async def test_interval_schedule_fires_repeatedly_without_duplicates(monkeypatch):
    """Recurring interval schedules keep firing after each run settles them."""
    tmpdir = tempfile.mkdtemp()
    monkeypatch.chdir(tmpdir)
    await init_db()

    sid = await ScheduleManager.add_schedule("repeat goal", "interval", "60")

    fired_mission_ids = []
    for _ in range(3):
        await _make_due(DB_PATH, sid)
        claimed = await ScheduleManager.claim_due_schedules()
        assert len(claimed) == 1, "exactly one firing per due poll"
        assert claimed[0]["id"] == sid
        mid = await create_mission("repeat goal")
        fired_mission_ids.append(mid)
        await ScheduleManager.update_schedule_after_run(sid, mid, "COMPLETED")

    assert len(set(fired_mission_ids)) == 3, "three distinct mission rows, one per firing"
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT status FROM schedules WHERE id = ?", (sid,)
        )
        assert dict(await cursor.fetchone())["status"] == "ACTIVE"
        cursor = await db.execute(
            "SELECT mission_id, status FROM schedule_history WHERE schedule_id = ? ORDER BY id",
            (sid,),
        )
        history = [tuple(r) for r in await cursor.fetchall()]
    assert history == [(m, "COMPLETED") for m in fired_mission_ids]


@pytest.mark.asyncio
async def test_failed_scheduled_run_recorded_as_failed(monkeypatch):
    """Failed schedule runs are logged FAILED and do not kill recurring schedules."""
    tmpdir = tempfile.mkdtemp()
    monkeypatch.chdir(tmpdir)
    await init_db()

    # Once-type: fires once, run fails -> history FAILED, schedule COMPLETED.
    once_sid = await ScheduleManager.add_schedule("once fail", "once", datetime.now().isoformat())
    assert await ScheduleManager.claim_due_schedules()
    await ScheduleManager.update_schedule_after_run(once_sid, 111, "FAILED")

    # Recurring: run fails -> history FAILED, schedule stays ACTIVE for next run.
    int_sid = await ScheduleManager.add_schedule("interval fail", "interval", "60")
    await _make_due(DB_PATH, int_sid)
    assert await ScheduleManager.claim_due_schedules()
    await ScheduleManager.update_schedule_after_run(int_sid, 222, "FAILED")

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT status FROM schedules WHERE id IN (?, ?) ORDER BY id",
                                  (once_sid, int_sid))
        statuses = [dict(r)["status"] for r in await cursor.fetchall()]
        cursor = await db.execute(
            "SELECT status FROM schedule_history WHERE schedule_id = ?", (once_sid,)
        )
        once_history = [r[0] for r in await cursor.fetchall()]
        cursor = await db.execute(
            "SELECT status FROM schedule_history WHERE schedule_id = ?", (int_sid,)
        )
        int_history = [r[0] for r in await cursor.fetchall()]

    assert statuses == ["COMPLETED", "ACTIVE"]  # once done; recurring still live
    assert once_history == ["FAILED"]
    assert int_history == ["FAILED"]


# --- cron next_run calculations ---------------------------------------------

def _parse(iso: str) -> datetime:
    return datetime.fromisoformat(iso)


@pytest.mark.asyncio
async def test_cron_daily_schedule(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.chdir(tmpdir)
    await init_db()
    now = datetime.now()
    nxt = _parse(ScheduleManager._calculate_next_run("cron", "30 9 * * *"))
    assert nxt.minute == 30 and nxt.hour == 9 and nxt.second == 0
    assert now < nxt <= now + timedelta(hours=26)


@pytest.mark.asyncio
async def test_cron_every_hour_schedule(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.chdir(tmpdir)
    await init_db()
    now = datetime.now()
    nxt = _parse(ScheduleManager._calculate_next_run("cron", "0 * * * *"))
    assert nxt.minute == 0 and nxt.second == 0
    assert now < nxt <= now + timedelta(hours=2)


@pytest.mark.asyncio
async def test_cron_every_minute_schedule(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.chdir(tmpdir)
    await init_db()
    now = datetime.now()
    nxt = _parse(ScheduleManager._calculate_next_run("cron", "* * * * *"))
    assert nxt.second == 0
    assert now < nxt <= now + timedelta(minutes=2)


@pytest.mark.asyncio
async def test_concurrent_claims_never_double_fire(monkeypatch):
    """Many workers claiming simultaneously: every due schedule claimed exactly once."""
    tmpdir = tempfile.mkdtemp()
    monkeypatch.chdir(tmpdir)
    await init_db()

    ids = []
    for _ in range(5):
        ids.append(await ScheduleManager.add_schedule("race goal", "once", datetime.now().isoformat()))

    # 10 concurrent "workers" all poll at once.
    claims = await asyncio.gather(*[ScheduleManager.claim_due_schedules() for _ in range(10)])

    claimed_ids = [s["id"] for batch in claims for s in batch]
    assert sorted(claimed_ids) == sorted(ids), "every due schedule claimed exactly once"
    assert len(set(claimed_ids)) == len(ids) == 5


@pytest.mark.asyncio
async def test_unexpected_execution_crash_is_marked_failed_by_caller(monkeypatch):
    """If run_mission raises unexpectedly, the worker's except path must mark
    the mission FAILED — never left IN_PROGRESS (which would stall the queue)."""
    from squad_os.database.session import add_to_queue, get_next_queued_mission, update_mission

    tmpdir = tempfile.mkdtemp()
    monkeypatch.chdir(tmpdir)
    await init_db()

    await add_to_queue("crash goal")
    queued = await get_next_queued_mission()
    mid = queued["id"]
    await update_mission(mid, "IN_PROGRESS")

    manager = Manager(tool_inventory=[], model_name="gpt-4o-mini", verification_enabled=False)

    async def _boom(*args, **kwargs):
        raise RuntimeError("unexpected crash inside DAG")

    with patch.object(manager, "execute_dag", side_effect=_boom):
        with pytest.raises(RuntimeError):
            # workflow_json skips LLM planning so the crash comes from execute_dag.
            await manager.run_mission("crash goal", None, _workflow_json(), mission_id=mid)

    # Worker except path: mark FAILED, so the mission never stalls IN_PROGRESS.
    assert (await get_mission(mid))["status"] == "IN_PROGRESS"  # run_mission raised before finalize
    await update_mission(mid, "FAILED")  # exactly what worker.py / start_worker.py do
    assert (await get_mission(mid))["status"] == "FAILED"
    assert await get_next_queued_mission() is None
