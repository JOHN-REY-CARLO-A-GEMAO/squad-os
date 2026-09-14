import json
import logging
import re
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, Field
from litellm import acompletion
import os
import shutil
from squad_os.agents.base import BaseAgent
from squad_os.database.session import (
    create_mission, get_all_personas, append_conversation, get_mission,
)
# Re-exported for callers/tests that import the final-status helper from here.
from squad_os.database.session_missions import compute_mission_final_status  # noqa: F401
from squad_os.orchestrator.run_store import RunStore, SessionRunStore
from squad_os.core.projects import ProjectBranch
from squad_os.core.utils import is_safe_path
from squad_os.orchestrator.mission_run import MissionRun, RunConfig
from squad_os.agents.verifier import VerifierAgent

class TaskPlan(BaseModel):
    description: str
    assigned_agent_role: str
    depends_on: List[int] = Field(default_factory=list, description="List of task indices (0-based) this task depends on")
    priority: int = Field(default=0, description="Task priority (higher = more urgent)")
    estimated_complexity: str = Field(default="medium", description="low, medium, or high")
    is_swarm: bool = Field(default=False, description="Whether this task should be executed as a swarm (multiple agents)")
    swarm_roles: List[str] = Field(default_factory=list, description="List of roles to include in the swarm if is_swarm is True")
    conditions: List[str] = Field(default_factory=list, description="Condition expressions gating this task (evaluated against parent outputs)")
    verification_gates: List[str] = Field(default_factory=list, description="Which gates to run: test_suite, lint, type_check, file_exists:<path>, all. Empty = default set.")

class MissionPlan(BaseModel):
    tasks: List[TaskPlan]
    suggested_parallelism: int = Field(default=2, description="Recommended number of concurrent tasks")


class Manager:
    def __init__(self, tool_inventory: List[Any], model_name: str = "gpt-4o-mini", verification_enabled: bool = True, store: Optional[RunStore] = None):
        self.tool_inventory = {t.name: t for t in tool_inventory}
        self.model_name = model_name
        self.max_retries = 3
        self.active_agents = {}
        self.plan_mission_obj = None
        self.verifier = VerifierAgent() if verification_enabled else None
        self.parent_event_ids = {}
        self.conversation_id = 1
        # Storage seam (staged commit 1): every run-state persistence call
        # goes through this port. Default adapter wraps the session functions;
        # tests may inject their own.
        self.store: RunStore = store if store is not None else SessionRunStore()

    def _repair_json(self, content: str) -> str:
        """Deep clean JSON, handling severe LLM hallucinations."""
        content = content.strip()
        # Optimization: Early return if basic structure is clean and parsable
        if not (content.startswith('{') and content.endswith('}')):
            # If it's markdown wrapped, clean that first
            if "```" in content:
                content = re.sub(r"```(?:json)?\s*(.*?)\s*```", r"\1", content, flags=re.DOTALL).strip()
        
        # Extract JSON object
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            content = content[start:end+1]
        
        content = content.replace('\r', '').replace('\n', ' ')

        import json
        try:
            json.loads(content)
            return content
        except json.JSONDecodeError:
            pass

        content = re.sub(r"'([a-zA-Z_][a-zA-Z0-9_]*)'\s*:", r'"\1":', content)
        return content

    async def recruit_squad(self, goal: str):
        # --- NEW: Short-circuit for simple greetings ---
        low_complexity_keywords = ["hi", "hello", "hey", "who are you", "what's up"]
        if goal.lower().strip() in low_complexity_keywords:
            print(f"👋 [Manager]: Simple greeting detected. Minimizing squad...")
            self.active_agents = {
                "Assistant": BaseAgent(
                    role="Assistant", 
                    goal="Respond politely to the user.", 
                    backstory="A helpful and concise assistant.",
                    tools=list(self.tool_inventory.values()), 
                    model_name=self.model_name
                )
            }
            return

        print(f"🧐 [Manager]: Analyzing job description and hiring specialists...")

        # Load custom personas from the database
        custom_personas = await get_all_personas()
        persona_context = ""
        if custom_personas:
            persona_context = "\nCUSTOM PERSONAS AVAILABLE:\n" + "\n".join([f"- {p['role']}: {p['goal']}" for p in custom_personas])

        tool_names = ", ".join(self.tool_inventory.keys())
        prompt = f"""You are an HR Director.
MISSION: {goal}
AVAILABLE TOOLS: {tool_names}{persona_context}

Hire a squad. Return ONLY a valid JSON object. DO NOT include any conversational text.
If a CUSTOM PERSONA fits the mission, prioritize hiring them.
Structure: {{ "squad": [ {{ "role": "...", "goal": "...", "backstory": "...", "tools_to_assign": ["tool_name"] }} ] }}"""

        for attempt in range(self.max_retries):
            try:
                response = await acompletion(model=self.model_name, messages=[{"role": "user", "content": prompt}])
                raw_content = response.choices[0].message.content
                print(f"\n🔍 [DEBUG] Raw LLM response (attempt {attempt+1}):\n{raw_content[:500]}...\n")
                cleaned = self._repair_json(raw_content)
                print(f"🔍 [DEBUG] Cleaned JSON:\n{cleaned[:500]}...\n")
                hire_data = json.loads(cleaned)

                self.active_agents = {}

                # Create a map of custom personas for easy lookup
                persona_map = {p['role']: p for p in custom_personas}

                for member in hire_data.get('squad', []):
                    role_name = member['role']

                    # Check if this is a custom persona
                    if role_name in persona_map:
                        p = persona_map[role_name]
                        tools_list = json.loads(p['tools'])
                        assigned = [self.tool_inventory[name] for name in tools_list if name in self.tool_inventory]
                        backstory = p['backstory']
                        goal_text = p['goal']
                    else:
                        assigned = [self.tool_inventory[name] for name in member.get('tools_to_assign', []) if name in self.tool_inventory]
                        backstory = member['backstory']
                        goal_text = member['goal']

                    if "commit_project" in self.tool_inventory and self.tool_inventory["commit_project"] not in assigned:
                        assigned.append(self.tool_inventory["commit_project"])

                    print(f"🤝 [Manager]: Hired '{role_name}'")
                    self.active_agents[role_name] = BaseAgent(
                        role=role_name, goal=goal_text, backstory=backstory,
                        tools=assigned, model_name=self.model_name
                    )
                return
            except Exception as e:
                print(f"🔄 [Manager]: Hiring JSON Error. Retrying... ({attempt+1}/{self.max_retries})")

        raise ValueError("Failed to parse Hiring JSON after max retries.")

    async def plan_mission(self, goal: str) -> MissionPlan:
        print(f"📋 [Manager]: Planning execution strategy...")
        roles = ", ".join([f"{a.role}" for a in self.active_agents.values()])

        prompt = f"""Mission: {goal}
Available Roles (EXACTLY these, do NOT invent others): {roles}

RULES:
1. Assign tasks ONLY to roles listed above. NEVER invent new roles.
2. If only "Assistant" is available, assign ALL tasks to "Assistant".
3. Every task description MUST specify which TOOL to use.
4. The LAST task MUST say: 'MUST use commit_project tool to commit all artifacts'.
5. Identify INDEPENDENT tasks that can run in PARALLEL and set their depends_on to [].
6. Tasks that need results from other tasks MUST list those task indices in depends_on.
7. Set priority (0-3) based on importance: 3=critical, 2=high, 1=normal, 0=low.
8. Estimate complexity: "low", "medium", "high".
9. For "high" complexity tasks, consider setting is_swarm to true and selecting 2-3 swarm_roles for consensus.
10. If the mission goal mentions gates (TestGate, LintGate, TypeCheckGate, file_exists:<path>, or 'all'), set verification_gates on the tasks that need them.
11. Return ONLY JSON. No other text.
Structure: {{ "tasks": [ {{ "description": "...", "assigned_agent_role": "...", "depends_on": [0, 1], "priority": 1, "estimated_complexity": "medium", "is_swarm": false, "swarm_roles": [], "verification_gates": [] }} ], "suggested_parallelism": 2 }}"""

        for attempt in range(self.max_retries):
            try:
                response = await acompletion(model=self.model_name, messages=[{"role": "user", "content": prompt}])
                cleaned = self._repair_json(response.choices[0].message.content)
                plan_dict = json.loads(cleaned)
                plan = MissionPlan(**plan_dict)
                # Validate all roles exist
                valid_roles = set(a.role for a in self.active_agents.values())
                for t in plan.tasks:
                    if t.assigned_agent_role not in valid_roles:
                         raise ValueError(f"Invalid role: {t.assigned_agent_role}")
                    for sr in t.swarm_roles:
                        if sr not in valid_roles:
                            raise ValueError(f"Invalid swarm role: {sr}")

                # Inject verification_gates from goal keywords for any task that has none set
                goal_lower = goal.lower()
                gate_keywords = {
                    "testsuite": "test_suite", "testgate": "test_suite", "test": "test_suite",
                    "lintgate": "lint", "lint": "lint",
                    "typecheckgate": "type_check", "type_check": "type_check",
                    "typecheck": "type_check", "mypy": "type_check",
                }
                implied_gates = set()
                for kw, gate_name in gate_keywords.items():
                    if kw in goal_lower:
                        implied_gates.add(gate_name)
                if "all" in goal_lower or "all gates" in goal_lower:
                    implied_gates = {"test_suite", "lint", "type_check"}
                if implied_gates:
                    for t in plan.tasks:
                        existing = set(g.lower() for g in t.verification_gates)
                        merged = list(implied_gates | existing)
                        t.verification_gates = merged
                    print(f"  [Manager]: Gates {implied_gates} applied to {len(plan.tasks)} task(s) (merged with any LLM-set gates).")

                return plan
            except Exception as e:
                print(f" [Manager]: Planning JSON Error. Retrying... ({attempt+1}/{self.max_retries})")

        # --- FATAL FALLBACK ---
        print("️ [Manager]: LLM failed to plan. Falling back to an auto-generated sequential plan.")
        fallback_tasks = []
        for i, role in enumerate(self.active_agents.keys()):
            fallback_tasks.append(TaskPlan(description=f"Execute your assigned goal: {self.active_agents[role].goal}", assigned_agent_role=role, depends_on=[i-1] if i > 0 else []))
        return MissionPlan(tasks=fallback_tasks)

    async def run_mission(self, goal: str, uploaded_files_json: Optional[str] = None, workflow_json: Optional[str] = None, mission_id: Optional[int] = None) -> str:
        if mission_id is None:
            mission_id = await create_mission(goal, uploaded_files_json, workflow_json)
        else:
            # Reuse the caller-provided mission row (worker queue/schedule dispatch)
            # so tasks, interrupts and events attach to the SAME mission — no duplicate rows.
            await self.store.update_mission(mission_id, "IN_PROGRESS")

        # Initialize Event Sourcing: create MISSION.STARTED event
        # Guarded: event/snapshot writes must not crash the mission if tables are missing.
        try:
            parent_id = await self.store.append_conversation_event(
                conversation_id=self.conversation_id,
                event_namespace="MISSION",
                event_type="STARTED",
                payload={
                    "goal": goal,
                    "message": f"Assistant spawned Mission #{mission_id} to {goal}."
                },
                mission_id=mission_id
            )
            self.parent_event_ids[mission_id] = parent_id

            # Initialize Mission Snapshot
            await self.store.update_mission_snapshot(
                mission_id=mission_id,
                status="IN_PROGRESS",
                progress=0.0,
                latest_thought="Planning the mission DAG and mobilizing agent specialists...",
                next_action="Execute the planned task waves.",
                eta=120,
                confidence="HIGH",
                token_usage=0,
                estimated_cost=0.0
            )
        except Exception as db_err:
            logging.error(f"Database error during mission init: {db_err}")

        # 1. Create a Shared Project Branch for the Mission
        slug = goal[:30]
        branch_id = ProjectBranch.create_id(slug)
        shared_branch = ProjectBranch(branch_id)
        shared_branch.fork()
        print(f"📂 [Manager]: Created shared mission branch: {branch_id}")

        # 2. Handle Uploaded Files
        enriched_goal = goal
        if uploaded_files_json:
            try:
                files = json.loads(uploaded_files_json)
                if files:
                    uploads_dir = os.path.join(shared_branch.project_path, "uploads")
                    os.makedirs(uploads_dir, exist_ok=True)

                    file_summaries = []
                    for f in files:
                        src = f['temp_path']
                        safe_name = os.path.basename(f['name'])
                        dest = os.path.join(uploads_dir, safe_name)

                        if os.path.exists(dest):
                            name, ext = os.path.splitext(safe_name)
                            safe_name = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
                            dest = os.path.join(uploads_dir, safe_name)
                            f['name'] = safe_name

                        if os.path.exists(src):
                            # Security: Validate that temp_path is within the expected uploads directory
                            # Use the actual root path for validation rather than a hardcoded string
                            # Default base validation to workspace/uploads, but respect absolute paths if validated by platform
                            validation_base = os.path.join(os.getcwd(), "workspace", "uploads")
                            if not is_safe_path(validation_base, src):
                                logging.warning(f"BLOCKED: Attempted path traversal via uploaded file temp_path: {src}")
                                continue

                            shutil.move(src, dest)
                            rel_path = os.path.relpath(dest, os.getcwd())
                            f['final_path'] = rel_path
                            file_summaries.append(f"- Filename: {f['name']}, Type: {f['type']}, Size: {f['size_bytes']//1024}KB, Path: {rel_path}")

                    if file_summaries:
                        header = f"\n\n--- UPLOADED FILES ({len(file_summaries)}) ---\n"
                        enriched_goal += header + "\n".join(file_summaries)

                    await self.store.update_mission_uploaded_files(mission_id, json.dumps(files))
            except Exception as e:
                print(f"⚠️ [Manager]: Error processing uploaded files: {e}")

        # 3. Either use pre-built workflow DAG or plan via LLM
        try:
            if workflow_json:
                self.active_agents = {}
                workflow_data = json.loads(workflow_json)
                tasks_data = workflow_data.get("tasks", [])
                suggested_parallelism = workflow_data.get("suggested_parallelism", 2)

                # Build agents for every unique role in the workflow
                all_roles = set()
                for t in tasks_data:
                    all_roles.add(t.get("assigned_agent_role", "Assistant"))
                    for sr in t.get("swarm_roles", []):
                        all_roles.add(sr)

                for role in all_roles:
                    self.active_agents[role] = BaseAgent(
                        role=role,
                        goal=f"Execute your assigned tasks in pre-built workflow: {goal[:50]}",
                        backstory=f"You are a {role} executing a predefined workflow from the Agent Store.",
                        tools=list(self.tool_inventory.values()),
                        model_name=self.model_name
                    )

                # Inject shared branch
                for agent in self.active_agents.values():
                    agent.active_branch = shared_branch

                # Build TaskPlan objects from the workflow data
                task_plans = []
                for i, t in enumerate(tasks_data):
                    task_plans.append(TaskPlan(
                        description=t.get("description", f"Task {i}"),
                        assigned_agent_role=t.get("assigned_agent_role", "Assistant"),
                        depends_on=t.get("depends_on", []),
                        priority=t.get("priority", 1),
                        estimated_complexity=t.get("estimated_complexity", "medium"),
                        is_swarm=t.get("is_swarm", False),
                        swarm_roles=t.get("swarm_roles", []),
                        conditions=t.get("conditions", [])
                    ))

                plan = MissionPlan(tasks=task_plans, suggested_parallelism=suggested_parallelism)
                self.plan_mission_obj = plan
                tasks = plan.tasks

                wf_name = workflow_data.get("name", "pre-built workflow")
                print(f"📋 [Manager]: Using pre-built workflow '{wf_name}' — skipping LLM planning.")
                for i, t in enumerate(tasks):
                    deps = f" (depends on: {t.depends_on})" if t.depends_on else ""
                    swarm = " [SWARM]" if t.is_swarm else ""
                    print(f"  📝 Task {i}{swarm}: [{t.assigned_agent_role}] {t.description}{deps}")
            else:
                await self.recruit_squad(enriched_goal)

                # Inject shared branch into all agents
                for agent in self.active_agents.values():
                    agent.active_branch = shared_branch

                plan = await self.plan_mission(enriched_goal)
                self.plan_mission_obj = plan  # Store for swarm access
                tasks = plan.tasks
                for i, t in enumerate(tasks):
                    deps = f" (depends on: {t.depends_on})" if t.depends_on else ""
                    swarm = " [SWARM]" if t.is_swarm else ""
                    print(f"  📝 Task {i}{swarm}: [{t.assigned_agent_role}] {t.description}{deps}")
        except Exception as e:
            print(f"❌ [Manager]: Setup failed: {e}")
            try:
                await self.store.update_mission(mission_id, "FAILED")
                await self.store.update_mission_snapshot(
                    mission_id=mission_id,
                    status="FAILED",
                    progress=1.0,
                    latest_thought=f"Mission setup failed: {str(e)}",
                    next_action="Review workspace logs.",
                    eta=0,
                    confidence="LOW",
                    token_usage=0,
                    estimated_cost=0.0
                )
                await self.store.append_conversation_event(
                    conversation_id=self.conversation_id,
                    event_namespace="ERROR",
                    event_type="COMPLETE",
                    payload={
                        "mission_id": mission_id,
                        "error": str(e),
                        "message": f"Mission #{mission_id} failed during setup."
                    },
                    parent_event_id=self.parent_event_ids.get(mission_id),
                    mission_id=mission_id
                )
            except Exception as db_err:
                logging.error(f"Database error while updating mission status: {db_err}")
            return "FAILED"

        # --- EXECUTE THE RUN ---
        # MissionRun owns the execution; the honest final status comes back on
        # the RunOutcome (strict grammar: anything not COMPLETED/SKIPPED —
        # including tasks awaiting human approval — fails the mission).
        run = self.make_run(mission_id, tasks, shared_branch)
        outcome = await run.execute(enriched_goal)

        # Final status
        try:
            final_status = outcome.status

            await self.store.update_mission(mission_id, final_status)
            await self.store.update_mission_snapshot(
                mission_id=mission_id,
                status=final_status,
                progress=1.0,
                latest_thought="Mission finalized." if final_status == "COMPLETED" else "Mission failed during parallel execution.",
                next_action="None." if final_status == "COMPLETED" else "Examine failure logs.",
                eta=0,
                confidence="HIGH" if final_status == "COMPLETED" else "LOW",
                token_usage=0,
                estimated_cost=0.0
            )
            await self.store.append_conversation_event(
                conversation_id=self.conversation_id,
                event_namespace="MISSION" if final_status == "COMPLETED" else "ERROR",
                event_type="COMPLETE",
                payload={
                    "mission_id": mission_id,
                    "message": f"Mission #{mission_id} finished with status: {final_status}"
                },
                parent_event_id=self.parent_event_ids.get(mission_id),
                mission_id=mission_id
            )
        except Exception as db_err:
            logging.error(f"Database error while updating mission status to final: {db_err}")
        return final_status

    async def handle_followup(self, mission_id: int, user_message: str):
        """Handle a follow-up message for an existing mission.
        Loads previous context, enriches the goal, re-plans, and re-executes on the same branch.
        """
        # 1. Load mission context
        mission = await get_mission(mission_id)
        if not mission:
            print(f"❌ [Manager]: Mission #{mission_id} not found for follow-up.")
            return

        goal = mission["goal"]
        prev_history = json.loads(mission.get("conversation_history") or "[]")
        workflow_json = mission.get("workflow_json")
        uploaded_files_json = mission.get("uploaded_files")

        # 2. Log the follow-up to conversation history
        await append_conversation(mission_id, "user", user_message)

        # 3. Build enriched goal from original + previous results + user follow-up
        enriched_goal = goal

        # Gather previous task results from DB
        prev_tasks = await self.store.get_mission_tasks(mission_id)

        if prev_tasks:
            summary_lines = ["\n\n--- PREVIOUS ATTEMPT RESULTS ---"]
            for i, t in enumerate(prev_tasks):
                status_icon = "✅" if t["status"] == "COMPLETED" else "❌"
                output = ""
                if t.get("output_data"):
                    try:
                        out = json.loads(t["output_data"])
                        output = f" → {str(out)[:200]}"
                    except (json.JSONDecodeError, TypeError):
                        output = f" → {str(t['output_data'])[:200]}"
                summary_lines.append(f"  Task {i} [{t['assigned_agent']}]: {status_icon} {t['description']}{output}")
            enriched_goal += "\n".join(summary_lines)

        enriched_goal += f"\n\n--- FOLLOW-UP FROM USER ---\n{user_message}"

        # 4. Load or recreate project branch
        slug = goal[:30]
        branch_id = ProjectBranch.create_id(slug)
        shared_branch = ProjectBranch(branch_id)
        if os.path.exists(shared_branch.project_path):
            print(f"📂 [Manager]: Reusing existing branch: {branch_id}")
        else:
            shared_branch.fork()
            print(f"📂 [Manager]: Created new shared mission branch: {branch_id}")

        # 5. Re-plan and re-execute
        try:
            await self.store.update_mission(mission_id, "IN_PROGRESS")
            await append_conversation(mission_id, "system", f"Re-planning with follow-up: {user_message[:100]}")

            if workflow_json:
                self.active_agents = {}
                workflow_data = json.loads(workflow_json)
                tasks_data = workflow_data.get("tasks", [])
                all_roles = set()
                for t in tasks_data:
                    all_roles.add(t.get("assigned_agent_role", "Assistant"))
                    for sr in t.get("swarm_roles", []):
                        all_roles.add(sr)
                for role in all_roles:
                    self.active_agents[role] = BaseAgent(
                        role=role,
                        goal=f"Execute your assigned tasks in pre-built workflow: {goal[:50]}",
                        backstory=f"You are a {role} executing a predefined workflow.",
                        tools=list(self.tool_inventory.values()),
                        model_name=self.model_name
                    )
                for agent in self.active_agents.values():
                    agent.active_branch = shared_branch

                task_plans = []
                for i, t in enumerate(tasks_data):
                    task_plans.append(TaskPlan(
                        description=t.get("description", f"Task {i}"),
                        assigned_agent_role=t.get("assigned_agent_role", "Assistant"),
                        depends_on=t.get("depends_on", []),
                        priority=t.get("priority", 1),
                        estimated_complexity=t.get("estimated_complexity", "medium"),
                        is_swarm=t.get("is_swarm", False),
                        swarm_roles=t.get("swarm_roles", [])
                    ))
                plan = MissionPlan(tasks=task_plans, suggested_parallelism=workflow_data.get("suggested_parallelism", 2))
                self.plan_mission_obj = plan
                tasks = plan.tasks
                print(f"📋 [Manager]: Follow-up using pre-built workflow — skipping LLM planning.")
            else:
                await self.recruit_squad(enriched_goal)
                for agent in self.active_agents.values():
                    agent.active_branch = shared_branch
                plan = await self.plan_mission(enriched_goal)
                self.plan_mission_obj = plan
                tasks = plan.tasks

            for i, t in enumerate(tasks):
                deps = f" (depends on: {t.depends_on})" if t.depends_on else ""
                print(f"  📝 Task {i}: [{t.assigned_agent_role}] {t.description}{deps}")

            await append_conversation(mission_id, "system", f"Re-planning complete — {len(tasks)} tasks to execute.")

            # Re-execute on the same branch: a fresh MissionRun for this follow-up
            run = self.make_run(mission_id, tasks, shared_branch)
            outcome = await run.execute(enriched_goal)
            await self.store.update_mission(mission_id, outcome.status)

            # Log outcome to conversation (honest mapping — FAILED runs are reported)
            await append_conversation(mission_id, "system", f"Follow-up execution complete. {outcome.summary}")

        except Exception as e:
            print(f"❌ [Manager]: Follow-up failed: {e}")
            await self.store.update_mission(mission_id, "FAILED")
            await append_conversation(mission_id, "system", f"Follow-up failed: {str(e)[:200]}")

    def make_run(self, mission_id: int, tasks: List[TaskPlan], shared_branch: Optional[ProjectBranch]) -> MissionRun:
        """Construct a MissionRun wired to this Manager's squad, store,
        verifier and config — the single construction point for runs
        (run_mission, handle_followup, and the Agent Store workflow tool).
        """
        return MissionRun(
            mission_id=mission_id,
            plan=MissionPlan(
                tasks=list(tasks),
                suggested_parallelism=getattr(self.plan_mission_obj, "suggested_parallelism", 2),
            ),
            agents=self.active_agents,
            branch=shared_branch,
            store=self.store,
            config=RunConfig(
                verification_enabled=self.verifier is not None,
                model_name=self.model_name,
                conversation_id=self.conversation_id,
            ),
            verifier=self.verifier,
            parent_event_ids=self.parent_event_ids,
        )
