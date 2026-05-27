import json
import logging
import re
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from litellm import acompletion
import os
import shutil
import aiosqlite
from squad_os.agents.base import BaseAgent
from squad_os.database.session import create_mission, create_task, update_task, update_mission, update_blackboard, DB_PATH, get_all_personas, append_conversation, get_conversation, get_mission, set_mission_status
from squad_os.core.projects import ProjectBranch
from squad_os.tools.self_healing import health_monitor
from squad_os.core.utils import is_safe_path
from squad_os.core.evaluator import SafeEvaluator, build_condition_context

class TaskPlan(BaseModel):
    description: str
    assigned_agent_role: str
    depends_on: List[int] = Field(default_factory=list, description="List of task indices (0-based) this task depends on")
    priority: int = Field(default=0, description="Task priority (higher = more urgent)")
    estimated_complexity: str = Field(default="medium", description="low, medium, or high")
    is_swarm: bool = Field(default=False, description="Whether this task should be executed as a swarm (multiple agents)")
    swarm_roles: List[str] = Field(default_factory=list, description="List of roles to include in the swarm if is_swarm is True")
    conditions: List[str] = Field(default_factory=list, description="Condition expressions gating this task (evaluated against parent outputs)")

class MissionPlan(BaseModel):
    tasks: List[TaskPlan]
    suggested_parallelism: int = Field(default=2, description="Recommended number of concurrent tasks")

class Manager:
    def __init__(self, tool_inventory: List[Any], model_name: str = "gpt-4o-mini"):
        self.tool_inventory = {t.name: t for t in tool_inventory}
        self.model_name = model_name
        self.max_retries = 3
        self.active_agents = {}
        self.agent_metrics = {}  # role -> {"tasks_completed": int, "tasks_failed": int, "total_time": float}
        self.agent_load = {}  # role -> current number of active tasks
        self.plan_mission_obj = None

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
                cleaned = self._repair_json(response.choices[0].message.content)
                hire_data = json.loads(cleaned)

                self.active_agents = {}
                commit_keywords = ["devops", "version control", "deployment", "release", "version", "coordinator", "control", "operator", "manager"]

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

                    role_lower = role_name.lower()
                    if any(kw in role_lower for kw in commit_keywords):
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
10. Return ONLY JSON. No other text.
Structure: {{ "tasks": [ {{ "description": "...", "assigned_agent_role": "...", "depends_on": [0, 1], "priority": 1, "estimated_complexity": "medium", "is_swarm": false, "swarm_roles": [] }} ], "suggested_parallelism": 2 }}"""

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
                return plan
            except Exception as e:
                print(f" [Manager]: Planning JSON Error. Retrying... ({attempt+1}/{self.max_retries})")

        # --- FATAL FALLBACK ---
        print("️ [Manager]: LLM failed to plan. Falling back to an auto-generated sequential plan.")
        fallback_tasks = []
        for i, role in enumerate(self.active_agents.keys()):
            fallback_tasks.append(TaskPlan(description=f"Execute your assigned goal: {self.active_agents[role].goal}", assigned_agent_role=role, depends_on=[i-1] if i > 0 else []))
        return MissionPlan(tasks=fallback_tasks)

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

    async def run_mission(self, goal: str, uploaded_files_json: Optional[str] = None, workflow_json: Optional[str] = None):
        mission_id = await create_mission(goal, uploaded_files_json, workflow_json)

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

                    async with aiosqlite.connect(DB_PATH) as db:
                        await db.execute("UPDATE missions SET uploaded_files = ? WHERE id = ?", (json.dumps(files), mission_id))
                        await db.commit()
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
                await update_mission(mission_id, "FAILED")
            except Exception as db_err:
                logging.error(f"Database error while updating mission status: {db_err}")
            return

        # --- EXECUTE DAG ---
        await self.execute_dag(tasks, mission_id, enriched_goal, shared_branch)

        # Final status
        try:
            await update_mission(mission_id, "COMPLETED")
        except Exception as db_err:
            logging.error(f"Database error while updating mission status to COMPLETED: {db_err}")

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
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT description, status, output_data, assigned_agent FROM tasks WHERE mission_id = ? ORDER BY id", (mission_id,))
            prev_tasks = [dict(r) for r in await cursor.fetchall()]

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
            await set_mission_status(mission_id, "IN_PROGRESS")
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

            # Re-execute on the same branch
            await self.execute_dag(tasks, mission_id, enriched_goal, shared_branch)
            await set_mission_status(mission_id, "COMPLETED")

            # Log success to conversation
            completed = sum(1 for t in self.plan_mission_obj.tasks if hasattr(t, '_result') and getattr(t, '_result') == "COMPLETED")
            await append_conversation(mission_id, "system", f"Follow-up execution complete. {completed}/{len(tasks)} tasks succeeded.")

        except Exception as e:
            print(f"❌ [Manager]: Follow-up failed: {e}")
            await set_mission_status(mission_id, "FAILED")
            await append_conversation(mission_id, "system", f"Follow-up failed: {str(e)[:200]}")

    async def execute_task(self, task_idx: int, context: str, mission_id: int, task_states, task_results, task_ids, tasks) -> bool:
        """Execute a single task. Returns True if successful."""
        task_data = tasks[task_idx]

        if task_data.is_swarm:
            return await self.execute_swarm_task(task_idx, context, mission_id, task_states, task_results, task_ids)

        agent = self.active_agents.get(task_data.assigned_agent_role)

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
            for r, a in self.active_agents.items():
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
        task_id = await create_task(mission_id, task_data.description, agent.role)
        task_ids[task_idx] = task_id

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

        # Update metrics
        self.agent_metrics[task_data.assigned_agent_role]["total_time"] += elapsed
        self.agent_load[task_data.assigned_agent_role] -= 1

        # Success path
        await update_task(task_id, status="COMPLETED", output_data=output_text)
        task_results[task_idx] = output_text
        task_states[task_idx] = "COMPLETED"
        self.agent_metrics[task_data.assigned_agent_role]["tasks_completed"] += 1
        health_monitor.record_success(task_data.assigned_agent_role)

        # Write result to blackboard for other tasks
        await update_blackboard(f"task_{task_idx}_result", output_text)

        print(f"✅ [Manager]: Task {task_idx} completed in {elapsed:.1f}s.")
        return True

    async def execute_swarm_task(self, task_idx: int, context: str, mission_id: int, task_states, task_results, task_ids) -> bool:
        """Execute a task using a swarm of agents for consensus."""
        task_data = self.plan_mission_obj.tasks[task_idx] if hasattr(self, 'plan_mission_obj') else None
        if not task_data:
             return False

        print(f"\n🐝 [Manager]: Starting SWARM for Task {task_idx}...")
        roles = [task_data.assigned_agent_role] + task_data.swarm_roles

        # 1. Parallel Execution
        async def agent_task(role: str):
            agent = self.active_agents.get(role)
            if not agent: return f"[{role}]: Agent not found."
            print(f"  🐝 [Swarm]: {role} is thinking...")
            try:
                result = await agent.execute_task(task_data.description, context)
                return f"[{role}]: {result.get('output', 'No output')}"
            except Exception as e:
                print(f"  ⚠️ [Swarm]: {role} failed: {e}")
                return f"[{role}]: FAILED - {str(e)}"

        outputs = await asyncio.gather(*[agent_task(r) for r in roles])
        debate_history = "\n\n".join(outputs)

        # 2. Consensus Building
        print(f"  🐝 [Swarm]: Building consensus between {len(roles)} agents...")
        consensus_prompt = f"""The following agents have provided their perspectives on the task:
{debate_history}

Original Task: {task_data.description}
Mission Context: {context}

Act as a Lead Coordinator. Synthesize these perspectives into a single, optimized final answer or plan of action.
Identify any conflicts and resolve them based on the best technical reasoning provided.
FINAL CONSENSUS:"""

        # Use the manager's model to synthesize
        response = await acompletion(model=self.model_name, messages=[{"role": "user", "content": consensus_prompt}])
        final_output = response.choices[0].message.content

        # 3. Record result
        task_id = await create_task(mission_id, f"[SWARM] {task_data.description}", "Manager (Consensus)")
        task_ids[task_idx] = task_id
        await update_task(task_id, status="COMPLETED", output_data=final_output)
        task_results[task_idx] = final_output
        task_states[task_idx] = "COMPLETED"

        print(f"✅ [Manager]: Swarm Task {task_idx} reached consensus.")
        return True

    async def execute_dag(self, tasks: List[TaskPlan], mission_id: int, enriched_goal: str, shared_branch: ProjectBranch):
        """DAG-BASED PARALLEL EXECUTION"""
        # State values: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "SKIPPED"
        task_states = {}
        task_results = {}  # task_idx -> output_text
        task_ids = {}  # task_idx -> database task_id
        
        for i in range(len(tasks)):
            task_states[i] = "PENDING"

        max_waves = len(tasks) * 2
        wave = 0
        _memory_written = False
        sem = asyncio.Semaphore(getattr(self.plan_mission_obj, 'suggested_parallelism', 2))
        
        while any(state == "PENDING" for state in task_states.values()) and wave < max_waves:
            wave += 1
            
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
                    task_id = await create_task(
                        mission_id, tasks[i].description, tasks[i].assigned_agent_role
                    )
                    task_ids[i] = task_id
                    await update_task(
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
                        task_id = await create_task(
                            mission_id, tasks[i].description, tasks[i].assigned_agent_role
                        )
                        task_ids[i] = task_id
                        await update_task(
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
            max_concurrent = getattr(self.plan_mission_obj, 'suggested_parallelism', 2)
            # Check if any agent is overloaded
            for task_idx in ready_tasks:
                role = tasks[task_idx].assigned_agent_role
                current_load = self.agent_load.get(role, 0)
                if current_load >= max_concurrent:
                    print(f"⚠️ [Manager]: Agent '{role}' is at capacity ({current_load} tasks). Deferring task {task_idx}.")
            
            # Execute in parallel (all ready tasks, load tracking happens inside execute_task)
            async def capped_execute(idx):
                async with sem:
                    return await self.execute_task(idx, task_contexts[idx], mission_id, task_states, task_results, task_ids, tasks)
            results = await asyncio.gather(*[capped_execute(idx) for idx in ready_tasks], return_exceptions=True)
            
            # Handle exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    task_idx = ready_tasks[i]
                    print(f"❌ [Manager]: Task {task_idx} failed with exception: {result}")
                    task_states[task_idx] = "FAILED"
                    if task_idx in task_ids:
                        try:
                            await update_task(task_ids[task_idx], status="FAILED", output_data=str(result))
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
                for role, agent in self.active_agents.items():
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
                    new_context = "\n\n".join(context_parts)
                    
                    # Retry
                    success = await self.execute_task(task_idx, new_context, mission_id, task_states, task_results, task_ids, tasks)
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

