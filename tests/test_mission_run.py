"""MissionRun interface tests (staged commit 2 of the MissionRun architecture).

Drives the run through its one interface — execute() — with fake agents and
the InMemoryRunStore adapter. Scenarios re-expressed from the deleted
test_hitl_flow.py and test_verification_retry.py (replace, don't layer),
plus the temporary cut-lines: the swarm executor injection and the Manager
execute_dag delegate.
"""
import json
import os
import sys
from types import SimpleNamespace

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from squad_os.core.gates import VerificationReport, GateResult
from squad_os.orchestrator.manager import Manager, MissionPlan, TaskPlan
from squad_os.orchestrator.mission_run import MissionRun, RunConfig, RunOutcome
from squad_os.orchestrator.run_store import InMemoryRunStore


# ── Test doubles ──────────────────────────────────────────────────────

class FakeDestructiveTool:
    destructive = True


class FakeAgent:
    def __init__(self, role="Analyst", output="This is a sufficiently long task output.",
                 tools=None, exc=None):
        self.role = role
        self.goal = "test"
        self.backstory = "test"
        self.tools = tools if tools is not None else {}
        self.active_branch = None
        self.task_workspace = None
        self.model_name = "test-model"
        self._output = output
        self._exc = exc
        self.contexts = []

    async def execute_task(self, description, context, model_override=None):
        self.contexts.append(context)
        if self._exc:
            raise self._exc
        return {"output": self._output}


class FakeBranch:
    def __init__(self, path):
        self.project_path = str(path)
        self.base_dir = str(path)
        self.task_id = "test-branch"


def make_run(tasks, agents, tmp_path, store=None, **kwargs):
    return MissionRun(
        mission_id=7,
        plan=MissionPlan(tasks=tasks),
        agents=agents,
        branch=FakeBranch(tmp_path),
        store=store if store is not None else InMemoryRunStore(),
        config=RunConfig(verification_enabled=False, conversation_id=1),
        **kwargs,
    )


# ── Outcome contract ─────────────────────────────────────────────────

async def test_outcome_completed_when_all_tasks_done(tmp_path):
    agent = FakeAgent()
    run = make_run([TaskPlan(description="do the thing", assigned_agent_role="Analyst")],
                   {"Analyst": agent}, tmp_path)
    outcome = await run.execute("mission goal")

    assert isinstance(outcome, RunOutcome)
    assert outcome.status == "COMPLETED"
    assert outcome.task_states == {0: "COMPLETED"}
    assert "1/1 completed" in outcome.summary
    # run state landed in the store, not in caller hands
    task_rows = await run.store.get_mission_tasks(7)
    assert task_rows[0]["status"] == "COMPLETED"
    assert run.store.blackboard["task_0_result"] == agent._output
    assert run.store.events  # THINKING + JOURNAL events written
    assert 7 in run.store.snapshots


# ── HITL: one-shot gate, rejection, resume ───────────────────────────

async def test_hitl_gate_fires_once(tmp_path, monkeypatch):
    """Approving a paused task must NOT re-create an interrupt."""
    store = InMemoryRunStore()
    agent = FakeAgent(tools={"python_runner": FakeDestructiveTool()})
    run = make_run(
        [TaskPlan(description="must use python_runner to compute stats",
                  assigned_agent_role="Analyst")],
        {"Analyst": agent}, tmp_path, store=store,
    )

    async def fake_prompt(*a, **kw):
        return ("decided", "APPROVED")

    monkeypatch.setattr(run, "_prompt_human_in_terminal", fake_prompt)
    outcome = await run.execute("g")

    assert outcome.status == "COMPLETED"
    assert len(store.interrupts) == 1, "the HITL gate must fire only once per task"
    assert store.interrupts[1]["status"] == "RESOLVED"
    assert store.interrupts[1]["user_guidance"] == "APPROVED"
    assert len(agent.contexts) == 1, "task executed exactly once"


async def test_hitl_rejection_fails_task(tmp_path, monkeypatch):
    store = InMemoryRunStore()
    agent = FakeAgent(tools={"python_runner": FakeDestructiveTool()})
    run = make_run(
        [TaskPlan(description="must use python_runner to do something",
                  assigned_agent_role="Analyst")],
        {"Analyst": agent}, tmp_path, store=store,
    )

    async def fake_prompt(*a, **kw):
        return ("decided", "reject this task, bad plan")

    monkeypatch.setattr(run, "_prompt_human_in_terminal", fake_prompt)
    outcome = await run.execute("g")

    assert outcome.status == "FAILED"
    assert outcome.task_states[0] == "FAILED"
    assert agent.contexts == [], "a rejected task is never executed"
    rows = await store.get_mission_tasks(7)
    assert rows[0]["status"] == "FAILED"


async def test_hitl_dashboard_resolution_behavior_is_preserved(tmp_path, monkeypatch):
    """Pins today's dashboard-resume behavior at the new interface.

    Pre-existing behavior, deliberately preserved by the extraction: a task
    re-queued after dashboard approval re-raises the HITL breakpoint on
    re-execution (the destructive tools are still attached), so it ends
    PAUSED_FOR_REVIEW and the strict policy fails the run. The old suite
    only covered terminal approval, which resolves inline instead. Worth
    revisiting when HITL gets its own seam — not this commit.
    """
    store = InMemoryRunStore()
    agent = FakeAgent(tools={"python_runner": FakeDestructiveTool()})
    run = make_run(
        [TaskPlan(description="must use python_runner tool to compute",
                  assigned_agent_role="Analyst")],
        {"Analyst": agent}, tmp_path, store=store,
    )

    async def fake_prompt(mission_id, task_idx, interrupt_id, context):
        # Human answers from the dashboard while the terminal stays quiet.
        await store.update_interrupt_guidance(interrupt_id, "APPROVED via dashboard")
        return ("undecided", "")

    monkeypatch.setattr(run, "_prompt_human_in_terminal", fake_prompt)
    outcome = await run.execute("g")

    assert outcome.task_states[0] == "PAUSED_FOR_REVIEW"
    assert outcome.status == "FAILED", "strict policy: paused means unfinished"
    assert run.status.value == "AWAITING_HUMAN"
    assert len(store.interrupts) == 2, "re-execution re-raises the breakpoint (pre-existing)"
    assert agent.contexts == [], "the task never actually executed"
    assert run.agent_load.get("Analyst", 0) == 0, "load released on each pause"


async def test_agent_load_released_after_inline_approval(tmp_path, monkeypatch):
    store = InMemoryRunStore()
    agent = FakeAgent(tools={"python_runner": FakeDestructiveTool()})
    run = make_run(
        [TaskPlan(description="must use python_runner tool to compute",
                  assigned_agent_role="Analyst")],
        {"Analyst": agent}, tmp_path, store=store,
    )

    async def fake_prompt(*a, **kw):
        return ("decided", "APPROVED")

    monkeypatch.setattr(run, "_prompt_human_in_terminal", fake_prompt)
    await run.execute("g")

    assert run.agent_load.get("Analyst", 0) == 0, "load must return to 0 after pause + execute"


# ── Scheduling: skips, failures ──────────────────────────────────────

async def test_condition_skip_propagates_to_dependents(tmp_path):
    parent = FakeAgent(output=json.dumps({"go": False}))
    child = FakeAgent()
    run = make_run(
        [
            TaskPlan(description="check whether to go", assigned_agent_role="Analyst"),
            TaskPlan(description="conditional step", assigned_agent_role="Analyst",
                     depends_on=[0], conditions=["go == True"]),
            TaskPlan(description="child of skipped", assigned_agent_role="Analyst",
                     depends_on=[1]),
        ],
        {"Analyst": parent, "Analyst2": child}, tmp_path,
    )
    outcome = await run.execute("g")

    assert outcome.task_states == {0: "COMPLETED", 1: "SKIPPED", 2: "SKIPPED"}
    assert outcome.status == "COMPLETED", "skipped is neutral"
    assert child.contexts == [], "skipped tasks never execute"


async def test_exception_fails_task_and_outcome(tmp_path):
    agent = FakeAgent(exc=ValueError("agent crashed"))
    run = make_run([TaskPlan(description="boom", assigned_agent_role="Analyst")],
                   {"Analyst": agent}, tmp_path)
    outcome = await run.execute("g")

    assert outcome.status == "FAILED"
    assert outcome.task_states[0] == "FAILED"
    rows = await run.store.get_mission_tasks(7)
    assert rows[0]["status"] == "FAILED"
    assert "agent crashed" in rows[0]["output_data"]


# ── Verification failure → reassignment retry with context ──────────

async def test_verification_failure_triggers_reassignment_retry(tmp_path):
    from unittest.mock import AsyncMock, MagicMock

    store = InMemoryRunStore()
    tmpdir = str(tmp_path)

    maker = FakeAgent(role="Maker", output="initial code")
    maker.active_branch = FakeBranch(tmpdir)
    fixer = FakeAgent(role="Fixer", output="fixed code")
    fixer.active_branch = FakeBranch(tmpdir)

    failed_report = VerificationReport(
        task_idx=0,
        task_description="write a script",
        results=[GateResult(status="FAIL", gate_name="test_suite",
                            details="test_example.py: assert 1+1==3", duration_ms=50.0)],
    )
    mock_verifier = MagicMock()
    mock_verifier.verify = AsyncMock(return_value=failed_report)

    run = make_run(
        [TaskPlan(description="write a script", assigned_agent_role="Maker")],
        {"Maker": maker, "Fixer": fixer}, tmp_path,
        store=store, verifier=mock_verifier,
    )
    outcome = await run.execute("write a script for me")

    assert maker.contexts, "Maker should have been called"
    assert "VERIFICATION" not in maker.contexts[0].upper(), "first attempt has no verification context"
    assert fixer.contexts, "failed task should be reassigned to the Fixer"
    retry_context = fixer.contexts[0]
    assert ("VERIFICATION" in retry_context.upper()
            or "test_suite" in retry_context
            or "1+1==3" in retry_context), "retry context carries gate failure details"
    assert outcome.status == "FAILED"  # Fixer also fails the same gates


# ── Temporary cut-line: swarm executor injection ─────────────────────

async def test_swarm_routes_to_injected_executor(tmp_path):
    store = InMemoryRunStore()
    calls = []
    tasks = [TaskPlan(description="swarm it", assigned_agent_role="Analyst",
                      is_swarm=True, swarm_roles=["Second"])]

    async def fake_swarm(task_idx, context, mission_id, task_states, task_results, task_ids):
        calls.append((task_idx, context, mission_id))
        tid = await store.create_task(mission_id, f"[SWARM] {tasks[0].description}",
                                      "Manager (Consensus)")
        task_ids[task_idx] = tid
        await store.update_task(tid, status="COMPLETED", output_data="consensus")
        task_results[task_idx] = "consensus"
        task_states[task_idx] = "COMPLETED"
        return True

    run = make_run(tasks, {"Analyst": FakeAgent(), "Second": FakeAgent()},
                   tmp_path, store=store, swarm_executor=fake_swarm)
    outcome = await run.execute("g")

    assert calls == [(0, "Mission: g", 7)], "swarm tasks route to the injected executor"
    assert outcome.status == "COMPLETED"
    assert outcome.task_states == {0: "COMPLETED"}


# ── Temporary cut-line: Manager execute_dag delegate ─────────────────

async def test_manager_execute_dag_delegates_to_mission_run(tmp_path):
    """The delegate keeps today's contract (per-task state map) and routes
    persistence through the Manager's injected store."""
    store = InMemoryRunStore()
    mgr = Manager(tool_inventory=[], model_name="test", verification_enabled=False, store=store)
    mgr.active_agents = {"Analyst": FakeAgent()}
    mgr.plan_mission_obj = SimpleNamespace(suggested_parallelism=2)

    result = await mgr.execute_dag(
        [TaskPlan(description="delegate me", assigned_agent_role="Analyst")],
        mission_id=7, enriched_goal="g", shared_branch=FakeBranch(tmp_path),
    )

    assert isinstance(result, dict), "delegate returns today's task-state map"
    assert result == {0: "COMPLETED"}
    rows = await store.get_mission_tasks(7)
    assert rows[0]["status"] == "COMPLETED", "the run used the Manager's store"
