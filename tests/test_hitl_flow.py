"""Regression tests for the HITL / execution fixes.

Covers the five bugs exposed when the new version was test-run:
  1. HITL gate re-firing forever (infinite approve loop)
  2. agent_load accounting leaking on the pause path (capacity spam)
  3. fake "Deferring" branch (removed)
  4. mission identity split + unconditional COMPLETED status
  5. terminal approval leaving interrupts PENDING forever
"""
import os
import sys
import asyncio
from types import SimpleNamespace

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import squad_os.orchestrator.manager as manager_mod
from squad_os.orchestrator.manager import (
    Manager, MissionPlan, TaskPlan, compute_mission_final_status,
)


@pytest.fixture(autouse=True)
async def _isolated_db(tmp_path, monkeypatch):
    """Hermetic DB: run every test on a fresh tmp database (mirrors the
    fresh-db convention). No dev-DB pollution, no missing-table flakes."""
    monkeypatch.chdir(tmp_path)
    from squad_os.database.session import init_db
    await init_db()


# ── Test doubles ──────────────────────────────────────────────────────

class FakeDestructiveTool:
    destructive = True


class FakeAgent:
    def __init__(self, role="Analyst", output="This is a sufficiently long task output."):
        self.role = role
        self.goal = "test"
        self.backstory = "test"
        self.tools = {"python_runner": FakeDestructiveTool()}
        self.active_branch = None
        self.task_workspace = None
        self.model_name = "test-model"
        self._output = output

    async def execute_task(self, description, context, model_override=None):
        return {"output": self._output}


async def _noop(*args, **kwargs):
    return None


# ── 1. One-shot HITL gate ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_hitl_gate_fires_once(monkeypatch):
    """Approving a paused task must NOT re-create an interrupt on the next wave."""
    mgr = Manager(tool_inventory=[], model_name="test", verification_enabled=False)
    mgr.active_agents = {"Analyst": FakeAgent()}
    mgr.plan_mission_obj = SimpleNamespace(suggested_parallelism=2)

    calls = {"interrupts": [], "tasks": [], "resolved": []}

    async def fake_create_interrupt(**kw):
        iid = len(calls["interrupts"]) + 1
        calls["interrupts"].append(iid)
        return iid

    async def fake_create_task(*a, **kw):
        return 100

    async def fake_update_task(task_id, **kw):
        calls["tasks"].append(kw.get("status"))

    async def fake_get_task_interrupt(*a, **kw):
        return {"id": 1, "status": "PENDING", "context": "x"}

    async def fake_update_interrupt_guidance(iid, guidance):
        calls["resolved"].append((iid, guidance))

    async def fake_prompt(*a, **kw):
        return ("decided", "APPROVED")

    monkeypatch.setattr(mgr.store, "create_interrupt", fake_create_interrupt)
    monkeypatch.setattr(mgr.store, "create_task", fake_create_task)
    monkeypatch.setattr(mgr.store, "update_task", fake_update_task)
    monkeypatch.setattr(mgr.store, "get_task_interrupt", fake_get_task_interrupt)
    monkeypatch.setattr(mgr.store, "update_interrupt_guidance", fake_update_interrupt_guidance)
    monkeypatch.setattr(mgr, "_prompt_human_in_terminal", fake_prompt)

    tasks = [TaskPlan(
        description="must use python_runner to compute stats",
        assigned_agent_role="Analyst", required_tier="fast",
    )]
    task_states = await mgr.execute_dag(tasks, mission_id=7, enriched_goal="g", shared_branch=None)
    final_status = compute_mission_final_status(task_states)

    assert final_status == "COMPLETED"
    assert len(calls["interrupts"]) == 1, "the HITL gate must fire only once per task"
    assert calls["tasks"].count("COMPLETED") == 1
    assert (1, "APPROVED") in calls["resolved"], "terminal approval must resolve the interrupt row"


@pytest.mark.asyncio
async def test_hitl_gate_respects_rejection(monkeypatch):
    """A rejected task is FAILED and is never executed."""
    mgr = Manager(tool_inventory=[], model_name="test", verification_enabled=False)
    mgr.active_agents = {"Analyst": FakeAgent()}
    mgr.plan_mission_obj = SimpleNamespace(suggested_parallelism=2)

    calls = {"interrupts": 0, "tasks": []}

    async def fake_create_interrupt(**kw):
        calls["interrupts"] += 1
        return calls["interrupts"]

    async def fake_create_task(*a, **kw):
        return 100

    async def fake_update_task(task_id, **kw):
        calls["tasks"].append(kw.get("status"))

    async def fake_get_task_interrupt(*a, **kw):
        return {"id": 1, "status": "PENDING", "context": "x"}

    async def fake_prompt(*a, **kw):
        return ("decided", "reject this task, bad plan")

    monkeypatch.setattr(mgr.store, "create_interrupt", fake_create_interrupt)
    monkeypatch.setattr(mgr.store, "create_task", fake_create_task)
    monkeypatch.setattr(mgr.store, "update_task", fake_update_task)
    monkeypatch.setattr(mgr.store, "get_task_interrupt", fake_get_task_interrupt)
    monkeypatch.setattr(mgr.store, "update_interrupt_guidance", _noop)
    monkeypatch.setattr(mgr, "_prompt_human_in_terminal", fake_prompt)

    tasks = [TaskPlan(
        description="must use python_runner to do something",
        assigned_agent_role="Analyst", required_tier="fast",
    )]
    task_states = await mgr.execute_dag(tasks, mission_id=7, enriched_goal="g", shared_branch=None)
    final_status = compute_mission_final_status(task_states)

    assert final_status == "FAILED"
    assert "FAILED" in calls["tasks"]
    assert calls["tasks"].count("COMPLETED") == 0


# ── 2. agent_load accounting ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_agent_load_zero_after_pause_and_execute(monkeypatch):
    """The pause path must not leak into agent_load; execution leaves it at 0."""
    mgr = Manager(tool_inventory=[], model_name="test", verification_enabled=False)
    mgr.active_agents = {"Analyst": FakeAgent()}
    mgr.plan_mission_obj = SimpleNamespace(suggested_parallelism=2)

    interrupt_count = {"n": 0}

    async def fake_create_interrupt(**kw):
        interrupt_count["n"] += 1
        return interrupt_count["n"]

    async def fake_get_task_interrupt(*a, **kw):
        return {"id": 1, "status": "PENDING", "context": "x"}

    async def fake_prompt(*a, **kw):
        return ("decided", "APPROVED")

    monkeypatch.setattr(mgr.store, "create_interrupt", fake_create_interrupt)
    monkeypatch.setattr(mgr.store, "create_task", lambda *a, **k: asyncio.sleep(0, result=100))
    monkeypatch.setattr(mgr.store, "update_task", _noop)
    monkeypatch.setattr(mgr.store, "get_task_interrupt", fake_get_task_interrupt)
    monkeypatch.setattr(mgr.store, "update_interrupt_guidance", _noop)
    monkeypatch.setattr(mgr, "_prompt_human_in_terminal", fake_prompt)

    tasks = [TaskPlan(
        description="must use python_runner tool to compute",
        assigned_agent_role="Analyst", required_tier="fast",
    )]
    await mgr.execute_dag(tasks, mission_id=8, enriched_goal="g", shared_branch=None)

    assert mgr.agent_load.get("Analyst", 0) == 0, "load must return to 0 after pause + execute"


# ── 3. Honest final mission status ────────────────────────────────────

def test_final_status_all_completed():
    assert compute_mission_final_status({0: "COMPLETED", 1: "COMPLETED"}) == "COMPLETED"


def test_final_status_completed_with_skipped():
    assert compute_mission_final_status({0: "COMPLETED", 1: "SKIPPED"}) == "COMPLETED"


def test_final_status_failed():
    assert compute_mission_final_status({0: "COMPLETED", 1: "FAILED"}) == "FAILED"


def test_final_status_paused_beats_failed():
    assert compute_mission_final_status({0: "PAUSED_FOR_REVIEW", 1: "FAILED"}) == "PAUSED_FOR_REVIEW"


def test_final_status_empty():
    assert compute_mission_final_status({}) == "COMPLETED"


# ── 4. Mission identity: run_mission reuses the queue row ─────────────

@pytest.mark.asyncio
async def test_run_mission_reuses_queue_mission_id(monkeypatch):
    mgr = Manager(tool_inventory=[], model_name="test", verification_enabled=False)

    calls = {"created": [], "updated": []}

    async def fake_create_mission(*a, **kw):
        calls["created"].append(a)
        return 999

    async def fake_update_mission(mid, status):
        calls["updated"].append((mid, status))

    async def fake_execute_dag(*a, **kw):
        return {0: "FAILED"}

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

    monkeypatch.setattr(manager_mod, "create_mission", fake_create_mission)
    monkeypatch.setattr(mgr.store, "update_mission", fake_update_mission)
    monkeypatch.setattr(manager_mod, "ProjectBranch", FakeBranch)
    monkeypatch.setattr(mgr, "execute_dag", fake_execute_dag)
    monkeypatch.setattr(mgr, "recruit_squad", _noop)
    monkeypatch.setattr(mgr, "plan_mission", fake_plan_mission)

    result = await mgr.run_mission("some goal", mission_id=42)

    assert calls["created"] == [], "run_mission must NOT create a duplicate mission row"
    assert (42, "IN_PROGRESS") in calls["updated"], "queue row should be marked IN_PROGRESS"
    assert (42, "FAILED") in calls["updated"], "final status must come from task outcomes"
    assert (42, "COMPLETED") not in calls["updated"], "no unconditional COMPLETED"
    assert result == "FAILED", "run_mission should return the honest outcome"


@pytest.mark.asyncio
async def test_run_mission_creates_when_no_id(monkeypatch):
    mgr = Manager(tool_inventory=[], model_name="test", verification_enabled=False)

    calls = {"created": [], "updated": []}

    async def fake_create_mission(*a, **kw):
        calls["created"].append(a)
        return 999

    async def fake_update_mission(mid, status):
        calls["updated"].append((mid, status))

    class FakeBranch:
        def __init__(self, bid):
            pass

        @classmethod
        def create_id(cls, slug):
            return "test-branch"

        def fork(self):
            pass

    async def fake_execute_dag(*a, **kw):
        return {0: "COMPLETED"}

    async def fake_plan_mission(goal):
        return MissionPlan(tasks=[
            TaskPlan(description="do something", assigned_agent_role="Analyst")
        ])

    monkeypatch.setattr(manager_mod, "create_mission", fake_create_mission)
    monkeypatch.setattr(mgr.store, "update_mission", fake_update_mission)
    monkeypatch.setattr(manager_mod, "ProjectBranch", FakeBranch)
    monkeypatch.setattr(mgr, "execute_dag", fake_execute_dag)
    monkeypatch.setattr(mgr, "recruit_squad", _noop)
    monkeypatch.setattr(mgr, "plan_mission", fake_plan_mission)

    await mgr.run_mission("some goal")

    assert calls["created"], "no mission_id given -> a mission row should be created"
    assert (999, "COMPLETED") in calls["updated"], "created mission should receive final status"
