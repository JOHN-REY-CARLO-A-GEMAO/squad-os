"""MissionRun — one execution of a Mission's task DAG (staged commit 2).

Owns the run state (task states, results, task ids), the wave scheduler,
HITL raise/resolve, verification gates, retries, event/snapshot writes
and the project-memory fallback, behind one interface: execute().

The Manager constructs a MissionRun after prep (recruit / plan / branch /
uploads) and maps the RunOutcome onto today's status grammar. Swarm
execution is injected as a temporary cut-line (staged commit 2); commit 3
folds it in and removes the injection.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional

from squad_os.agents.verifier import VerifierAgent
from squad_os.core.evaluator import SafeEvaluator, build_condition_context
from squad_os.core.projects import ProjectBranch
from squad_os.orchestrator.run_store import RunStore
from squad_os.tools.self_healing import health_monitor

if TYPE_CHECKING:  # runtime: `plan` is accessed structurally (tasks, suggested_parallelism)
    from squad_os.orchestrator.manager import MissionPlan


class RunStatus(str, Enum):
    """Live status of a MissionRun."""
    RUNNING = "RUNNING"
    AWAITING_HUMAN = "AWAITING_HUMAN"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class RunOutcome:
    """What MissionRun.execute() returns.

    status uses the strict external grammar ("COMPLETED" | "FAILED"):
    anything not COMPLETED/SKIPPED — including tasks paused awaiting
    human approval — fails the run, matching run_mission's contract.
    """
    status: str
    task_states: Dict[int, str]
    summary: str = ""


@dataclass
class RunConfig:
    """Knobs a run needs; planning-side retries stay on the Manager."""
    verification_enabled: bool = True
    model_name: str = "gpt-4o-mini"  # swarm consensus synthesis (consumed when swarm folds in, commit 3)
    conversation_id: int = 1


# Temporary cut-line (staged commit 2): Manager.execute_swarm_task is passed
# in with today's signature; commit 3 folds the swarm into MissionRun.
SwarmExecutor = Callable[..., Awaitable[bool]]


class MissionRun:
    """One execution of a Mission's task DAG. See CONTEXT.md."""

    def __init__(
        self,
        mission_id: int,
        plan: "MissionPlan",
        agents: Dict[str, Any],
        branch: Optional[ProjectBranch],
        store: RunStore,
        config: Optional[RunConfig] = None,
        *,
        verifier: Optional[VerifierAgent] = None,
        swarm_executor: Optional[SwarmExecutor] = None,
        parent_event_ids: Optional[Dict[int, int]] = None,
    ):
        self.mission_id = mission_id
        self.plan = plan
        self.tasks = list(plan.tasks)
        self.agents = dict(agents)
        self.branch = branch
        self.store = store
        self.config = config or RunConfig()
        if verifier is not None:
            self.verifier = verifier
        else:
            self.verifier = VerifierAgent() if self.config.verification_enabled else None
        self._swarm_executor = swarm_executor
        self.parent_event_ids = parent_event_ids if parent_event_ids is not None else {}
        self.verification_disabled_tasks: set = set()

        # Run state — owned here, never visible to callers (CONTEXT.md).
        self.task_states: Dict[int, str] = {}
        self.task_results: Dict[int, str] = {}
        self.task_ids: Dict[int, int] = {}
        self.agent_metrics: Dict[str, Dict[str, Any]] = {}
        self.agent_load: Dict[str, int] = {}
        self._status = RunStatus.RUNNING

    @property
    def status(self) -> RunStatus:
        return self._status

    def _write_project_memory(self, branch, goal: str, tasks: List, task_results: Dict[int, str], waves: int):
        """Auto-generate a comprehensive project_memory.md after mission completion."""
        from datetime import datetime
        import os

        memory_path = os.path.join(branch.project_path, "project_memory.md")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Scan all generated files in the branch
        all_files = []
        total_size = 0
        for root, dirs, files in os.walk(branch.project_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for f in files:
                if f.startswith('.'):
                    continue
                rel = os.path.relpath(os.path.join(root, f), branch.project_path)
                fpath = os.path.join(root, f)
                size = os.path.getsize(fpath)
                total_size += size
                all_files.append((rel, size))

        lines = []
        lines.append(f"# Project Memory: {branch.task_id}")
        lines.append("")
        lines.append(f"**Mission:** {goal}")
        lines.append(f"**Completed:** {now}")
        lines.append(f"**Waves executed:** {waves}")
        lines.append(f"**Files generated:** {len(all_files)} ({total_size:,} bytes)")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Task summary
        lines.append("## Task Execution Summary")
        lines.append("")
        for i in sorted(task_results.keys()):
            desc = tasks[i].description if i < len(tasks) else f"Task {i}"
            result_preview = task_results[i][:300].replace("\n", " ")
            lines.append(f"### Task {i}: {desc}")
            lines.append(f"> {result_preview}")
            lines.append("")

        # File inventory
        lines.append("## Generated Files")
        lines.append("")
        lines.append("| File | Size |")
        lines.append("|------|------|")
        for rel, size in sorted(all_files, key=lambda x: x[0]):
            lines.append(f"| {rel} | {size:,} B |")
        lines.append("")

        # Agent performance
        lines.append("## Agent Performance")
        lines.append("")
        lines.append("| Agent | Success Rate | Avg Time | Health |")
        lines.append("|-------|-------------|----------|--------|")
        for role, metrics in sorted(self.agent_metrics.items()):
            total = metrics["tasks_completed"] + metrics["tasks_failed"]
            if total > 0:
                rate = f"{metrics['tasks_completed']}/{total} ({metrics['tasks_completed']/total*100:.0f}%)"
                avg = f"{metrics['total_time'] / max(1, metrics['tasks_completed']):.1f}s"
                health = "✅" if metrics['tasks_failed'] == 0 else "⚠️"
                lines.append(f"| {role} | {rate} | {avg} | {health} |")
        lines.append("")

        content = "\n".join(lines)

        with open(memory_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"📝 [Manager]: Auto-generated project_memory.md ({len(all_files)} files, {total_size:,} bytes)")

    async def _prompt_human_in_terminal(self, mission_id: int, task_idx: int, interrupt_id: int, context: str):
        """Terminal fast-path for HITL approval. Returns (decision, guidance).

        Default is undecided (async dashboard flow resolves via wave loop).
        Tests monkeypatch this hook to simulate terminal approval/rejection.
        """
        return ("undecided", "")

    async def _execute_task(self, task_idx: int, context: str) -> bool:
        """Execute a single task. Returns True if successful.

        Moved verbatim from Manager.execute_task (staged commit 2); the
        run state is now owned by this instance instead of threaded
        through parameters.
        """
        mission_id = self.mission_id
        task_states = self.task_states
        task_results = self.task_results
        task_ids = self.task_ids
        tasks = self.tasks
        task_data = tasks[task_idx]

        if task_data.is_swarm:
            return await self._swarm_executor(task_idx, context, mission_id, task_states, task_results, task_ids)

        agent = self.agents.get(task_data.assigned_agent_role)

        # Initialize agent metrics if not present (Fix 3)
        if task_data.assigned_agent_role not in self.agent_metrics:
            self.agent_metrics[task_data.assigned_agent_role] = {
                "tasks_completed": 0,
                "tasks_failed": 0,
                "total_time": 0.0
            }
            
        # Initialize load tracking if not present
        if task_data.assigned_agent_role not in self.agent_load:
            self.agent_load[task_data.assigned_agent_role] = 0

        # Track load
        self.agent_load[task_data.assigned_agent_role] += 1

        # Fuzzy match fallback
        if not agent:
            target = str(task_data.assigned_agent_role).lower()
            for r, a in self.agents.items():
                if r.lower() in target or target in r.lower():
                    agent = a
                    break

        if not agent:
            print(f"⚠️ [Manager]: Skipping task {task_idx}, role '{task_data.assigned_agent_role}' not found.")
            task_states[task_idx] = "FAILED"
            
            # Safe metric update to prevent KeyError (Redundant check for safety)
            if task_data.assigned_agent_role not in self.agent_metrics:
                self.agent_metrics[task_data.assigned_agent_role] = {"tasks_completed": 0, "tasks_failed": 0, "total_time": 0.0}
            
            self.agent_metrics[task_data.assigned_agent_role]["tasks_failed"] += 1
            
            # Safe load update
            if task_data.assigned_agent_role in self.agent_load:
                self.agent_load[task_data.assigned_agent_role] -= 1
            else:
                self.agent_load[task_data.assigned_agent_role] = 0
                
            health_monitor.record_failure(task_data.assigned_agent_role, "Agent role not found in active agents")
            return False

        print(f"\n🚀 [Manager]: Task {task_idx}/{len(tasks)} -> {agent.role}")
        task_id = await self.store.create_task(mission_id, task_data.description, agent.role)
        task_ids[task_idx] = task_id

        # Event Sourcing: Log TOOL.THINKING event
        await self.store.append_conversation_event(
            conversation_id=self.config.conversation_id,
            event_namespace="TOOL",
            event_type="THINKING",
            payload={
                "agent": agent.role,
                "thought": f"Starting task: {task_data.description}",
                "confidence": "HIGH"
            },
            parent_event_id=self.parent_event_ids.get(mission_id),
            mission_id=mission_id
        )

        # Update Mission Snapshot progress
        completed_count = sum(1 for s in task_states.values() if s == "COMPLETED")
        total_count = len(tasks)
        progress = completed_count / total_count if total_count > 0 else 0.0
        await self.store.update_mission_snapshot(
            mission_id=mission_id,
            status="IN_PROGRESS",
            progress=progress,
            latest_thought=f"Agent '{agent.role}' is starting task: {task_data.description}",
            next_action="Working on wave tasks.",
            eta=90,
            confidence="HIGH",
            token_usage=0,
            estimated_cost=0.0
        )

        # Create per-task isolated workspace so parallel agents don't collide
        if agent.active_branch:
            task_workspace = os.path.join(agent.active_branch.project_path, f"task_{task_idx}")
            os.makedirs(task_workspace, exist_ok=True)
            agent.task_workspace = task_workspace
            print(f"  [Manager]: Task {task_idx} isolated workspace: {task_workspace}")

        # --- HITL BREAKPOINT ---
        # If the agent carries destructive tools, pause for human review before executing.
        destructive_names = [n for n, t in agent.tools.items() if getattr(t, 'destructive', False)]
        if destructive_names:
            interrupt_id = await self.store.create_interrupt(
                mission_id=mission_id,
                task_idx=task_idx,
                context=f"Agent '{agent.role}' has access to destructive tools: {destructive_names}. Task: {task_data.description}",
                error_message=f"Task paused: destructive tools ({', '.join(destructive_names)}) require human approval."
            )
            await self.store.update_task(task_id, status="PAUSED_FOR_REVIEW")
            task_states[task_idx] = "PAUSED_FOR_REVIEW"

            # Event Sourcing: Log INBOX.APPROVAL_REQUESTED event
            await self.store.append_conversation_event(
                conversation_id=self.config.conversation_id,
                event_namespace="INBOX",
                event_type="APPROVAL_REQUESTED",
                payload={
                    "approval_id": interrupt_id,
                    "status": "PENDING",
                    "message": f"Task paused: destructive tools ({', '.join(destructive_names)}) require human approval.",
                    "changes_summary": task_data.description
                },
                parent_event_id=self.parent_event_ids.get(mission_id),
                mission_id=mission_id
            )

            # Update snapshot status to FOLLOWUP
            await self.store.update_mission_snapshot(
                mission_id=mission_id,
                status="FOLLOWUP",
                progress=progress,
                latest_thought=f"Task {task_idx} paused for human-in-the-loop validation of destructive tools.",
                next_action="Awaiting user approval in the AI Inbox.",
                eta=0,
                confidence="MEDIUM",
                token_usage=0,
                estimated_cost=0.0
            )

            print(f"  [HITL]: Task {task_idx} paused (interrupt #{interrupt_id}). Destructive tools: {destructive_names}")

            # Release the worker slot while paused so agent_load doesn't leak.
            self.agent_load[task_data.assigned_agent_role] = max(0, self.agent_load.get(task_data.assigned_agent_role, 0) - 1)

            # Terminal fast-path: resolve inline if a human is at the terminal.
            try:
                _decision, _guidance = await self._prompt_human_in_terminal(
                    mission_id=mission_id, task_idx=task_idx,
                    interrupt_id=interrupt_id, context=task_data.description,
                )
            except Exception:
                _decision, _guidance = ("undecided", "")
            _guidance_text = (_guidance or "").strip()
            if _guidance_text.upper().startswith("APPROVED"):
                await self.store.update_interrupt_guidance(interrupt_id, _guidance_text)
                print(f"  [HITL]: Task {task_idx} approved in terminal. Proceeding.")
                # Fall through to normal execution below (no re-pause, no new interrupt).
            elif _guidance_text and _guidance_text.upper() not in ("PENDING", "UNDECIDED"):
                await self.store.update_interrupt_guidance(interrupt_id, _guidance_text)
                await self.store.update_task(task_id, status="FAILED",
                                  error=f"Rejected by human: {_guidance_text}")
                task_states[task_idx] = "FAILED"
                self.agent_metrics[task_data.assigned_agent_role]["tasks_failed"] += 1
                health_monitor.record_failure(task_data.assigned_agent_role, f"Rejected by human: {_guidance_text[:200]}")
                print(f"  [HITL]: Task {task_idx} rejected by human.")
                return False
            else:
                return True  # Not a failure — DAG will check back once human resolves

        start_time = datetime.now()
        try:
            result = await agent.execute_task(task_data.description, context)
        finally:
            elapsed = (datetime.now() - start_time).total_seconds()
            self.agent_load[task_data.assigned_agent_role] = max(0, self.agent_load.get(task_data.assigned_agent_role, 0) - 1)

        output_text = result.get("output", "Task completed without text summary.")

        # --- TOOL ENFORCEMENT CHECK ---
        must_use = "must use" in task_data.description.lower() or "delegate_task" in task_data.description.lower()
        if must_use and len(output_text) < 20 and "DELEGATED" not in output_text:
            print(f"️ [Manager]: Agent {agent.role} skipped mandatory tool use. Forcing retry...")
            # Retry once with enforcement context
            retry_context = context + f"\n\nERROR: You skipped a mandatory tool call. You MUST execute the tool now."
            result = await agent.execute_task(task_data.description, retry_context)
            output_text = result.get("output", "Task completed without text summary.")

        # Update metrics (load is released once, in the finally above)
        self.agent_metrics[task_data.assigned_agent_role]["total_time"] += elapsed

        # --- VERIFICATION GATE ---
        # The maker never grades its own work. An external oracle checks it.
        verification_passed = True
        verification_report = None
        if self.verifier and task_idx not in self.verification_disabled_tasks and agent.active_branch:
            # Resolve workspace with fallback chain:
            # 1. task_workspace (if set and still exists)
            # 2. project root (if exists)
            # 3. archive path (if project was archived mid-task)
            workspace = (agent.task_workspace if agent.task_workspace and os.path.isdir(agent.task_workspace)
                         else agent.active_branch.project_path if os.path.isdir(agent.active_branch.project_path)
                         else None)
            if workspace is None:
                archive_candidate = os.path.join(agent.active_branch.base_dir, "archives", agent.active_branch.task_id)
                if os.path.isdir(archive_candidate):
                    workspace = archive_candidate
            if workspace:
                print(f"  [Verifier]: Running gates against task {task_idx} workspace...")
                gate_names = task_data.verification_gates if task_data.verification_gates else None
                report = await self.verifier.verify(
                    workspace=workspace,
                    task_description=task_data.description,
                    agent_output=output_text,
                    task_idx=task_idx,
                    gate_names=gate_names,
                )
                if report.all_required_passed:
                    # Enforce: if gates were explicitly requested but none could execute, treat as failure
                    if task_data.verification_gates and not report.results:
                        print(f"  [Verifier]: Task {task_idx} — required gates {task_data.verification_gates} could NOT be executed (no matching gate implementations).")
                        verification_passed = False
                        verification_report = report.to_dict()
                        verification_report["reason"] = f"Required gates {task_data.verification_gates} have no matching implementation"
                    else:
                        print(f"  [Verifier]: Task {task_idx} — all gates PASSED ({report.total_duration_ms:.0f}ms)")
                else:
                    print(f"  [Verifier]: Task {task_idx} — gates FAILED ({report.total_duration_ms:.0f}ms)")
                    print(f"  [Verifier]: Report:\n{report.summary()}")
                    verification_passed = False
                    verification_report = report.to_dict()
            else:
                print(f"  [Verifier]: Task {task_idx} workspace not found (project was archived by commit). Skipping file gates for meta-task.")

        # Success path (only if verification passed)
        if verification_passed:
            await self.store.update_task(task_id, status="COMPLETED", output_data=output_text,
                              verification_status="PASSED" if verification_report else "NOT_VERIFIED",
                              verification_details=json.dumps(verification_report) if verification_report else None)
            task_results[task_idx] = output_text
            task_states[task_idx] = "COMPLETED"
            self.agent_metrics[task_data.assigned_agent_role]["tasks_completed"] += 1
            health_monitor.record_success(task_data.assigned_agent_role)

            # Write result to blackboard for other tasks
            await self.store.update_blackboard(f"task_{task_idx}_result", output_text)

            # Event Sourcing: Log TOOL.JOURNAL event
            await self.store.append_conversation_event(
                conversation_id=self.config.conversation_id,
                event_namespace="TOOL",
                event_type="JOURNAL",
                payload={
                    "agent": agent.role,
                    "status": "COMPLETED",
                    "output": output_text
                },
                parent_event_id=self.parent_event_ids.get(mission_id),
                mission_id=mission_id
            )

            # Update Mission Snapshot
            completed_count = sum(1 for s in task_states.values() if s == "COMPLETED")
            total_count = len(tasks)
            progress = completed_count / total_count if total_count > 0 else 1.0
            await self.store.update_mission_snapshot(
                mission_id=mission_id,
                status="IN_PROGRESS" if progress < 1.0 else "COMPLETED",
                progress=progress,
                latest_thought=f"Task {task_idx} completed successfully by '{agent.role}'.",
                next_action="Resolving next tasks.",
                eta=max(0, 90 - 30 * completed_count),
                confidence="HIGH",
                token_usage=0,
                estimated_cost=0.0
            )

            print(f"✅ [Manager]: Task {task_idx} completed in {elapsed:.1f}s.")
            return True
        else:
            await self.store.update_task(task_id, status="FAILED", output_data=output_text,
                              error=f"Verification failed: {json.dumps(verification_report)[:500]}",
                              verification_status="FAILED",
                              verification_details=json.dumps(verification_report))
            task_results[task_idx] = output_text
            task_states[task_idx] = "FAILED"
            self.agent_metrics[task_data.assigned_agent_role]["tasks_failed"] += 1
            health_monitor.record_failure(task_data.assigned_agent_role, f"Verification failed: {json.dumps(verification_report)[:200]}")

            # Event Sourcing: Log ERROR.JOURNAL event
            await self.store.append_conversation_event(
                conversation_id=self.config.conversation_id,
                event_namespace="ERROR",
                event_type="JOURNAL",
                payload={
                    "agent": agent.role,
                    "status": "FAILED",
                    "error": f"Verification failed or execution error: {output_text}"
                },
                parent_event_id=self.parent_event_ids.get(mission_id),
                mission_id=mission_id
            )

            # Update Mission Snapshot status to FAILED
            completed_count = sum(1 for s in task_states.values() if s == "COMPLETED")
            total_count = len(tasks)
            progress = completed_count / total_count if total_count > 0 else 1.0
            await self.store.update_mission_snapshot(
                mission_id=mission_id,
                status="FAILED",
                progress=progress,
                latest_thought=f"Task {task_idx} failed during execution or verification.",
                next_action="Examine error logs and resolve.",
                eta=0,
                confidence="LOW",
                token_usage=0,
                estimated_cost=0.0
            )

            print(f"❌ [Manager]: Task {task_idx} FAILED verification in {elapsed:.1f}s.")
            return False

    async def execute(self, context: str = "") -> RunOutcome:
        """Run the mission's task DAG to completion.

        Moved verbatim from Manager.execute_dag (staged commit 2). The
        run state (task_states / task_results / task_ids) is owned by
        this instance; the wave scheduler, HITL resolution, conditions
        and reassignment all live behind this interface.
        """
        tasks = self.tasks
        mission_id = self.mission_id
        enriched_goal = context
        shared_branch = self.branch
        # State values: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "SKIPPED" | "PAUSED_FOR_REVIEW"
        task_states = self.task_states
        task_results = self.task_results  # task_idx -> output_text
        task_ids = self.task_ids  # task_idx -> database task_id
        
        for i in range(len(tasks)):
            task_states[i] = "PENDING"

        max_waves = len(tasks) * 2
        wave = 0
        _memory_written = False
        sem = asyncio.Semaphore(getattr(self.plan, 'suggested_parallelism', 2))
        
        while (any(state in ("PENDING", "PAUSED_FOR_REVIEW") for state in task_states.values())
               and wave < max_waves):
            wave += 1

            # --- HITL RESOLUTION CHECK ---
            # If a PAUSED_FOR_REVIEW task's interrupt has been resolved by the human,
            # either approve (re-queue as PENDING) or reject (mark FAILED with guidance).
            for i in range(len(tasks)):
                if task_states.get(i) != "PAUSED_FOR_REVIEW":
                    continue
                interrupt = await self.store.get_task_interrupt(mission_id, i)
                if interrupt and interrupt["status"] == "RESOLVED":
                    guidance = (interrupt.get("user_guidance") or "").strip()
                    if guidance.upper().startswith("APPROVED"):
                        print(f"  [HITL]: Task {i} approved by human. Resuming.")
                        task_states[i] = "PENDING"
                        if i in task_ids:
                            await self.store.update_task(task_ids[i], status="PENDING")
                    else:
                        print(f"  [HITL]: Task {i} rejected by human: {guidance}")
                        task_states[i] = "FAILED"
                        if i in task_ids:
                            await self.store.update_task(task_ids[i], status="FAILED",
                                              error=f"Rejected by human: {guidance}")

            # Find tasks that are ready to execute
            ready_tasks = []
            for i in range(len(tasks)):
                if task_states[i] != "PENDING":
                    continue
                
                # Check if all dependencies are in a terminal state (COMPLETED or SKIPPED)
                deps = tasks[i].depends_on
                if not all(task_states.get(dep) in ("COMPLETED", "SKIPPED") for dep in deps):
                    continue
                
                # If a parent was SKIPPED, auto-skip child (condition cannot be met)
                if any(task_states.get(dep) == "SKIPPED" for dep in deps):
                    task_states[i] = "SKIPPED"
                    task_id = await self.store.create_task(
                        mission_id, tasks[i].description, tasks[i].assigned_agent_role
                    )
                    task_ids[i] = task_id
                    await self.store.update_task(
                        task_id, status="SKIPPED",
                        output_data="Parent task was skipped — condition branch unreachable."
                    )
                    print(f"⏭️ [Manager]: Task {i} auto-skipped — parent task skipped")
                    continue
                
                # Evaluate conditions from squad.yaml
                conditions = getattr(tasks[i], "conditions", [])
                if conditions:
                    ctx = build_condition_context(task_results, deps)
                    if not all(SafeEvaluator.evaluate(c, ctx) for c in conditions):
                        task_states[i] = "SKIPPED"
                        task_id = await self.store.create_task(
                            mission_id, tasks[i].description, tasks[i].assigned_agent_role
                        )
                        task_ids[i] = task_id
                        await self.store.update_task(
                            task_id, status="SKIPPED",
                            output_data=f"Condition not met: {'; '.join(conditions)}"
                        )
                        print(f"⏭️ [Manager]: Task {i} skipped — conditions not met: {conditions}")
                        continue
                
                ready_tasks.append(i)
            
            # Sort by priority (higher first), then by dependency count (fewer deps first)
            ready_tasks.sort(key=lambda idx: (-tasks[idx].priority, len(tasks[idx].depends_on)))
            
            if not ready_tasks:
                # Check for circular dependencies or failed dependencies
                pending_with_failed_deps = []
                for i in range(len(tasks)):
                    if task_states[i] == "PENDING":
                        deps = tasks[i].depends_on
                        if any(task_states.get(dep) == "FAILED" for dep in deps):
                            pending_with_failed_deps.append(i)
                
                if pending_with_failed_deps:
                    print(f"⚠️ [Manager]: Tasks {pending_with_failed_deps} have failed dependencies. Skipping.")
                    for i in pending_with_failed_deps:
                        task_states[i] = "FAILED"
                    continue
                else:
                    print(f"⚠️ [Manager]: No tasks ready to execute. Possible circular dependency.")
                    break
            
            # Write project memory before the commit task runs (branch gets archived after)
            for task_idx in ready_tasks:
                if "commit_project" in tasks[task_idx].description.lower():
                    try:
                        self._write_project_memory(shared_branch, enriched_goal, tasks, task_results, wave)
                    except Exception as e:
                        print(f"⚠️ [Manager]: Failed to write project memory: {e}")
                    _memory_written = True

            # Execute ready tasks in parallel
            print(f"\n🔄 [Manager]: Wave {wave} - Executing {len(ready_tasks)} tasks in parallel: {ready_tasks}")
            
            # Build context for each task from its dependencies
            task_contexts = {}
            for task_idx in ready_tasks:
                context_parts = [f"Mission: {enriched_goal}"]
                for dep_idx in tasks[task_idx].depends_on:
                    if dep_idx in task_results:
                        context_parts.append(f"Result from Task {dep_idx}: {task_results[dep_idx]}")
                task_contexts[task_idx] = "\n\n".join(context_parts)
            
            # Limit parallelism based on plan suggestion and agent load
            max_concurrent = getattr(self.plan, 'suggested_parallelism', 2)
            # Check if any agent is overloaded
            for task_idx in ready_tasks:
                role = tasks[task_idx].assigned_agent_role
                current_load = self.agent_load.get(role, 0)
                if current_load >= max_concurrent:
                    print(f"⚠️ [Manager]: Agent '{role}' is at capacity ({current_load} tasks). Deferring task {task_idx}.")
            
            # Execute in parallel (all ready tasks, load tracking happens inside execute_task)
            async def capped_execute(idx):
                async with sem:
                    return await self._execute_task(idx, task_contexts[idx])
            results = await asyncio.gather(*[capped_execute(idx) for idx in ready_tasks], return_exceptions=True)
            
            # Handle exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    task_idx = ready_tasks[i]
                    print(f"❌ [Manager]: Task {task_idx} failed with exception: {result}")
                    task_states[task_idx] = "FAILED"
                    if task_idx in task_ids:
                        try:
                            await self.store.update_task(task_ids[task_idx], status="FAILED", output_data=str(result))
                        except Exception as db_err:
                            logging.error(f"Failed to update task {task_idx} status: {db_err}")
                    
                    role = tasks[task_idx].assigned_agent_role
                    if role not in self.agent_metrics:
                        self.agent_metrics[role] = {"tasks_completed": 0, "tasks_failed": 0, "total_time": 0.0}
                    self.agent_metrics[role]["tasks_failed"] += 1
                    
                    health_monitor.record_failure(role, str(result))
        
        # --- DYNAMIC TASK REASSIGNMENT ---
        # Retry failed tasks with different agents if available
        failed_tasks = [i for i, state in task_states.items() if state == "FAILED"]
        if failed_tasks:
            print(f"\n🔄 [Manager]: Attempting to reassign {len(failed_tasks)} failed task(s)...")
            for task_idx in failed_tasks:
                original_role = tasks[task_idx].assigned_agent_role
                # Find alternative agents
                for role, agent in self.agents.items():
                    if role == original_role:
                        continue
                    # Skip if this agent is already heavily loaded
                    if self.agent_load.get(role, 0) > 2:
                        continue
                    
                    print(f"🔄 [Manager]: Reassigning task {task_idx} from '{original_role}' to '{role}'")
                    task_states[task_idx] = "PENDING"
                    tasks[task_idx].assigned_agent_role = role
                    
                    # Rebuild context
                    context_parts = [f"Mission: {enriched_goal}"]
                    for dep_idx in tasks[task_idx].depends_on:
                        if dep_idx in task_results:
                            context_parts.append(f"Result from Task {dep_idx}: {task_results[dep_idx]}")
                    # Inject previous verification failure details
                    if task_idx in task_ids:
                        try:
                            prev_task = await self.store.get_task(task_ids[task_idx])
                            if prev_task and prev_task.get("verification_details"):
                                details = json.loads(prev_task["verification_details"])
                                context_parts.append(
                                    f"--- PREVIOUS ATTEMPT VERIFICATION FAILURES ---\n"
                                    f"The previous attempt failed automated verification. "
                                    f"Fix the specific issues below:\n"
                                    f"{json.dumps(details, indent=2)}"
                                )
                                print(f"  [Manager]: Injected verification failure context for task {task_idx} retry.")
                        except Exception as e:
                            logging.warning(f"Could not load verification details for task {task_idx}: {e}")
                    new_context = "\n\n".join(context_parts)
                    
                    # Retry
                    success = await self._execute_task(task_idx, new_context)
                    if success:
                        print(f"✅ [Manager]: Task {task_idx} successfully reassigned and completed.")
                    else:
                        print(f"❌ [Manager]: Task {task_idx} reassignment also failed.")
                    break  # Only try one reassignment per task
        
        # Auto-generate project memory (fallback if no commit task ran)
        if not _memory_written:
            try:
                self._write_project_memory(shared_branch, enriched_goal, tasks, task_results, wave)
            except Exception as e:
                print(f"⚠️ [Manager]: Failed to write project memory: {e}")

        # Final status
        completed = sum(1 for s in task_states.values() if s == "COMPLETED")
        failed = sum(1 for s in task_states.values() if s == "FAILED")
        skipped = sum(1 for s in task_states.values() if s == "SKIPPED")
        total = len(tasks)
        print(f"📊 [Manager]: DAG complete — {completed}/{total} completed, {skipped} skipped, {failed} failed")
        
        # Agent performance report
        print(f"\n📊 [Manager]: Agent Performance Report:")
        for role, metrics in self.agent_metrics.items():
            total = metrics["tasks_completed"] + metrics["tasks_failed"]
            if total > 0:
                avg_time = metrics["total_time"] / max(1, metrics["tasks_completed"])
                success_rate = (metrics["tasks_completed"] / total) * 100
                print(f"   {role}: {metrics['tasks_completed']}/{total} succeeded ({success_rate:.0f}%), avg {avg_time:.1f}s/task")

        # Final outcome (strict policy, matching run_mission's external
        # grammar: anything not COMPLETED/SKIPPED — including tasks still
        # awaiting human approval — fails the mission).
        final_states = dict(self.task_states)
        unfinished = [s for s in final_states.values() if s not in ("COMPLETED", "SKIPPED")]
        final = "FAILED" if unfinished else "COMPLETED"
        paused = any(s == "PAUSED_FOR_REVIEW" for s in final_states.values())
        self._status = RunStatus.AWAITING_HUMAN if paused else RunStatus(final)
        completed_n = sum(1 for s in final_states.values() if s == "COMPLETED")
        skipped_n = sum(1 for s in final_states.values() if s == "SKIPPED")
        failed_n = sum(1 for s in final_states.values() if s == "FAILED")
        return RunOutcome(
            status=final,
            task_states=final_states,
            summary=f"{completed_n}/{len(final_states)} completed, {skipped_n} skipped, {failed_n} failed",
        )
