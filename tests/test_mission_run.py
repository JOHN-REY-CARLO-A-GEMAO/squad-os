"""MissionRun interface tests (staged commits 2-3 of the MissionRun architecture).

Drives the run through its one interface — execute() — with fake agents and
the InMemoryRunStore adapter. Scenarios re-expressed from the deleted
test_hitl_flow.py and test_verification_retry.py (replace, don't layer),
plus the routing: Manager.make_run is the single construction point, swarm
consensus lives inside the run, and follow-ups map RunOutcome honestly.
"""
import json
import os
import sys
from types import SimpleNamespace

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import squad_os.orchestrator.manager as manager_mod
import squad_os.orchestrator.mission_run as mission_run_mod
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


# ── Swarm: fan-out + consensus inside the run ────────────────────────

async def test_swarm_task_reaches_consensus(tmp_path, monkeypatch):
    from unittest.mock import MagicMock

    store = InMemoryRunStore()
    lead = FakeAgent(role="Analyst", output="perspective A")
    second = FakeAgent(role="Second", output="perspective B")
    run = make_run(
        [TaskPlan(description="swarm it", assigned_agent_role="Analyst",
                  is_swarm=True, swarm_roles=["Second"])],
        {"Analyst": lead, "Second": second}, tmp_path, store=store,
    )

    consensus = MagicMock()
    consensus.choices = [MagicMock(message=MagicMock(content="FINAL CONSENSUS: combine both"))]

    async def fake_acompletion(**kw):
        return consensus

    monkeypatch.setattr(mission_run_mod, "acompletion", fake_acompletion)
    outcome = await run.execute("g")

    assert outcome.status == "COMPLETED"
    assert outcome.task_states == {0: "COMPLETED"}
    assert len(lead.contexts) == 1 and len(second.contexts) == 1, "all swarm roles executed"
    rows = await store.get_mission_tasks(7)
    assert rows[0]["assigned_agent"] == "Manager (Consensus)"
    assert "FINAL CONSENSUS" in rows[0]["output_data"]


# ── Routing: Manager constructs runs, maps outcomes honestly ─────────

async def test_run_mission_routes_through_mission_run_and_injected_store(tmp_path, monkeypatch):
    """Manager → MissionRun → injected store, end to end: the run executes
    the squad's tasks and the final status lands through the seam."""
    store = InMemoryRunStore()
    mgr = Manager(tool_inventory=[], model_name="test", verification_enabled=False, store=store)
    agent = FakeAgent()
    mgr.active_agents = {"Analyst": agent}

    class FakeBranch:
        def __init__(self, bid):
            self.project_path = str(tmp_path)
            self.base_dir = str(tmp_path)
            self.task_id = "test-branch"

        @classmethod
        def create_id(cls, slug):
            return "test-branch"

        def fork(self):
            pass

    async def fake_plan_mission(goal):
        return MissionPlan(
            tasks=[TaskPlan(description="do the thing", assigned_agent_role="Analyst")],
            suggested_parallelism=2,
        )

    async def _noop(*a, **k):
        return None

    async def fake_create_mission(*a, **k):
        return 99

    monkeypatch.setattr(manager_mod, "create_mission", fake_create_mission)
    monkeypatch.setattr(manager_mod, "ProjectBranch", FakeBranch)
    monkeypatch.setattr(mgr, "recruit_squad", _noop)
    monkeypatch.setattr(mgr, "plan_mission", fake_plan_mission)

    result = await mgr.run_mission("some goal")

    assert result == "COMPLETED"
    assert store.mission_status[99] == "COMPLETED", "final status written through the injected store"
    assert store.mission_status.get(99) is not None
    rows = await store.get_mission_tasks(99)
    assert rows[0]["status"] == "COMPLETED", "the run executed through MissionRun"


@pytest.fixture
async def _isolated_db(tmp_path, monkeypatch):
    """Hermetic real DB for follow-up routing (handle_followup reads the
    mission row and conversation through the session package)."""
    monkeypatch.chdir(tmp_path)
    from squad_os.database.session import init_db
    await init_db()


async def test_handle_followup_runs_fresh_run_and_maps_outcome_honestly(tmp_path, _isolated_db, monkeypatch):
    """A follow-up is a fresh MissionRun on the same mission row; the run's
    outcome maps honestly onto the mission status (this pins the deliberate
    commit-3 change: FAILED runs are no longer reported as COMPLETED)."""
    from squad_os.database import session as session_mod

    mission_id = await session_mod.create_mission("original goal")
    mgr = Manager(tool_inventory=[], model_name="test", verification_enabled=False)
    mgr.active_agents = {"Broken": FakeAgent(role="Broken", exc=RuntimeError("nope"))}

    async def fake_plan_mission(goal):
        return MissionPlan(tasks=[TaskPlan(description="fix it", assigned_agent_role="Broken")])

    class FakeBranch:
        def __init__(self, bid):
            self.project_path = str(tmp_path)
            self.base_dir = str(tmp_path)
            self.task_id = "test-branch"

        @classmethod
        def create_id(cls, slug):
            return "test-branch"

        def fork(self):
            pass

    async def _noop(*a, **k):
        return None

    monkeypatch.setattr(manager_mod, "ProjectBranch", FakeBranch)
    monkeypatch.setattr(mgr, "recruit_squad", _noop)
    monkeypatch.setattr(mgr, "plan_mission", fake_plan_mission)

    await mgr.handle_followup(mission_id, "please fix it")

    mission = await session_mod.get_mission(mission_id)
    assert mission["status"] == "FAILED", "honest mapping: the follow-up run failed"
    history = await session_mod.get_conversation(mission_id)
    assert any("Follow-up execution complete" in (m.get("content") or "") for m in history), \
        "outcome summary logged to the conversation"
