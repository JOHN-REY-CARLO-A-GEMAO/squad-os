"""RunStore seam tests (staged commit 1 of the MissionRun architecture).

Proves the storage seam:
  1. SessionRunStore satisfies the RunStore protocol.
  2. Manager defaults to SessionRunStore and honours store injection —
     run-state writes go through the port, not module globals.
  3. SessionRunStore delegates to the session functions with the same
     behaviour the Manager had when it called them directly.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import squad_os.orchestrator.manager as manager_mod
from squad_os.database import session as session_mod
from squad_os.database.session import init_db
from squad_os.orchestrator.manager import Manager, MissionPlan, TaskPlan
from squad_os.orchestrator.mission_run import RunOutcome
from squad_os.orchestrator.run_store import RunStore, SessionRunStore


@pytest.fixture(autouse=True)
async def _isolated_db(tmp_path, monkeypatch):
    """Hermetic DB: fresh tmp database per test (mirrors test_hitl_flow)."""
    monkeypatch.chdir(tmp_path)
    await init_db()


# ── 1. Protocol conformance ──────────────────────────────────────────

def test_session_run_store_satisfies_protocol():
    assert isinstance(SessionRunStore(), RunStore)


# ── 2. Manager honours the seam ──────────────────────────────────────

def test_manager_defaults_to_session_run_store():
    mgr = Manager(tool_inventory=[], model_name="test", verification_enabled=False)
    assert isinstance(mgr.store, SessionRunStore)


async def test_run_mission_routes_status_through_injected_store(monkeypatch):
    """Mission status writes must cross the injected seam, not module globals."""
    updates = []

    class FakeStore:
        async def update_mission(self, mission_id, status):
            updates.append((mission_id, status))

        async def append_conversation_event(self, **kw):
            return None

        async def update_mission_snapshot(self, **kw):
            return None

    mgr = Manager(
        tool_inventory=[], model_name="test", verification_enabled=False,
        store=FakeStore(),
    )
    assert mgr.store.__class__ is FakeStore

    class FakeRun:
        async def execute(self, context=""):
            return RunOutcome(status="FAILED", task_states={0: "FAILED"}, summary="0/1 completed, 0 skipped, 1 failed")

    async def fake_plan_mission(goal):
        return MissionPlan(tasks=[
            TaskPlan(description="do something", assigned_agent_role="Analyst")
        ])

    class FakeBranch:
        def __init__(self, bid):
            pass

        @classmethod
        def create_id(cls, slug):
            return "test-branch"

        def fork(self):
            pass

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(manager_mod, "create_mission", _noop)  # prep stays module-level
    monkeypatch.setattr(manager_mod, "ProjectBranch", FakeBranch)
    monkeypatch.setattr(mgr, "make_run", lambda *a, **k: FakeRun())
    monkeypatch.setattr(mgr, "recruit_squad", _noop)
    monkeypatch.setattr(mgr, "plan_mission", fake_plan_mission)

    result = await mgr.run_mission("some goal", mission_id=42)

    assert result == "FAILED"
    assert (42, "IN_PROGRESS") in updates, "queue row marked IN_PROGRESS through the store"
    assert (42, "FAILED") in updates, "final status written through the store"
    assert (42, "COMPLETED") not in updates, "no unconditional COMPLETED"


# ── 3. SessionRunStore delegates to shared memory ────────────────────

async def test_session_run_store_delegates_to_shared_memory():
    store = SessionRunStore()
    mission_id = await session_mod.create_mission("seam delegation test")

    # Task lifecycle
    task_id = await store.create_task(mission_id, "do the thing", "Maker")
    assert isinstance(task_id, int)
    await store.update_task(task_id, status="FAILED", error="boom")
    task = await store.get_task(task_id)
    assert task["status"] == "FAILED"
    assert task["error"] == "boom"

    # Mission task listing (the follow-up enrichment read)
    tasks = await store.get_mission_tasks(mission_id)
    assert [t["description"] for t in tasks] == ["do the thing"]
    assert tasks[0]["assigned_agent"] == "Maker"

    # Mission status + staged upload metadata
    await store.update_mission(mission_id, "IN_PROGRESS")
    await store.update_mission_uploaded_files(mission_id, json.dumps([{"name": "a.txt"}]))
    mission = await session_mod.get_mission(mission_id)
    assert mission["status"] == "IN_PROGRESS"
    assert json.loads(mission["uploaded_files"])[0]["name"] == "a.txt"

    # HITL interrupts
    interrupt_id = await store.create_interrupt(
        mission_id, task_idx=0, context="destructive tools", error_message="paused",
    )
    fetched = await store.get_task_interrupt(mission_id, 0)
    assert fetched["id"] == interrupt_id
    assert fetched["status"] == "PENDING"
    await store.update_interrupt_guidance(interrupt_id, "APPROVED proceed")
    fetched = await store.get_task_interrupt(mission_id, 0)
    assert fetched["status"] == "RESOLVED"
    assert fetched["user_guidance"] == "APPROVED proceed"

    # Blackboard
    await store.update_blackboard("seam_key", "seam_value")
    assert await session_mod.read_blackboard("seam_key") == "seam_value"

    # Event log
    event_id = await store.append_conversation_event(
        conversation_id=1, event_namespace="MISSION", event_type="STARTED",
        payload={"goal": "seam test"}, mission_id=mission_id,
    )
    assert isinstance(event_id, int)

    # Mission snapshot (upsert)
    await store.update_mission_snapshot(mission_id, status="IN_PROGRESS", progress=0.5)
    snapshot = await session_mod.get_mission_snapshot(mission_id)
    assert snapshot is not None
    assert snapshot["status"] == "IN_PROGRESS"
    assert snapshot["progress"] == 0.5

    # Final status helper
    assert store.final_status({0: "COMPLETED", 1: "FAILED"}) == "FAILED"
    assert store.final_status({}) == "COMPLETED"


# ── Final-status precedence (re-expressed from the deleted test_hitl_flow) ──

def test_final_status_precedence_matrix():
    store = SessionRunStore()
    assert store.final_status({0: "COMPLETED", 1: "COMPLETED"}) == "COMPLETED"
    assert store.final_status({0: "COMPLETED", 1: "SKIPPED"}) == "COMPLETED"
    assert store.final_status({0: "COMPLETED", 1: "FAILED"}) == "FAILED"
    assert store.final_status({0: "PAUSED_FOR_REVIEW", 1: "FAILED"}) == "PAUSED_FOR_REVIEW"
    assert store.final_status({}) == "COMPLETED"
