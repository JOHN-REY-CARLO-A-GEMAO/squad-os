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
from squad_os.database.session import create_mission, create_task, update_task, update_mission, update_blackboard, DB_PATH
from squad_os.core.projects import ProjectBranch
from squad_os.tools.self_healing import health_monitor
from squad_os.core.utils import is_safe_path

class TaskPlan(BaseModel):
    description: str
    assigned_agent_role: str
    depends_on: List[int] = Field(default_factory=list, description="List of task indices (0-based) this task depends on")
    priority: int = Field(default=0, description="Task priority (higher = more urgent)")
    estimated_complexity: str = Field(default="medium", description="low, medium, or high")

class MissionPlan(BaseModel):
    tasks: List[TaskPlan]
    suggested_parallelism: int = Field(default=2, description="Recommended number of concurrent tasks")

class Manager:
    def __init__(self, tool_inventory: List[Any], model_name: str = "gpt-4o-mini"):
        self.tool_inventory = {t.name: t for t in tool_inventory}
        self.model_name = model_name
        self.max_retries = 3
        self.active_agents = {}
        self.agent_metrics = {}  # role -> {"tasks_completed": int, "tasks_failed": int, "avg_time": float}
        self.agent_load = {}  # role -> current number of active tasks

    def _repair_json(self, content: str) -> str:
        """Deep clean JSON, handling severe LLM hallucinations."""
        content = content.strip()
        if "```" in content:
            content = re.sub(r"```(?:json)?\s*(.*?)\s*```", r"\1", content, flags=re.DOTALL).strip()
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            content = content[start:end+1]
        content = content.replace('\r', '').replace('\n', ' ')

        # Only attempt quote repair if JSON is invalid and looks like it uses single quotes for keys
        # This regex specifically targets JSON property keys: 'property_name': value
        # It uses word boundary and lookahead to avoid matching apostrophes inside string values
        import json
        try:
            json.loads(content)
            return content  # Valid JSON, no repair needed
        except json.JSONDecodeError:
            pass  # Need repair

        # Check if it looks like single-quoted JSON (property names in single quotes)
        # Only match: 'word_chars': (property names) not: 'any content with spaces'
        # This avoids mangling contractions like O'Brien or don't
        # Pattern: single quote, followed by word chars (no spaces/apostrophes), then quote-colon
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
        tool_names = ", ".join(self.tool_inventory.keys())
        prompt = f"""You are an HR Director.
MISSION: {goal}
AVAILABLE TOOLS: {tool_names}

Hire a squad. Return ONLY a valid JSON object. DO NOT include any conversational text.
Structure: {{ "squad": [ {{ "role": "...", "goal": "...", "backstory": "...", "tools_to_assign": ["tool_name"] }} ] }}"""

        for attempt in range(self.max_retries):
            try:
                response = await acompletion(model=self.model_name, messages=[{"role": "user", "content": prompt}])
                cleaned = self._repair_json(response.choices[0].message.content)
                hire_data = json.loads(cleaned)

                self.active_agents = {}
                commit_keywords = ["devops", "version control", "deployment", "release", "version", "coordinator", "control", "operator", "manager"]
                for member in hire_data.get('squad', []):
                    assigned = [self.tool_inventory[name] for name in member.get('tools_to_assign', []) if name in self.tool_inventory]
                    role_lower = member['role'].lower()
                    if any(kw in role_lower for kw in commit_keywords):
                        if "commit_project" in self.tool_inventory and self.tool_inventory["commit_project"] not in assigned:
                            assigned.append(self.tool_inventory["commit_project"])
                    print(f"🤝 [Manager]: Hired '{member['role']}'")
                    self.active_agents[member['role']] = BaseAgent(
                        role=member['role'], goal=member['goal'], backstory=member['backstory'],
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
1. Assign tasks ONLY to roles listed above. NEVER invent new roles like Researcher, Analyst, Writer, Editor, etc.
2. If only "Assistant" is available, assign ALL tasks to "Assistant".
3. Every task description MUST specify which TOOL to use.
4. The LAST task MUST say: 'MUST use commit_project tool to commit all artifacts'.
5. Identify INDEPENDENT tasks that can run in PARALLEL and set their depends_on to [].
6. Tasks that need results from other tasks MUST list those task indices in depends_on.
7. Set priority (0-3) based on importance: 3=critical, 2=high, 1=normal, 0=low.
8. Estimate complexity: "low" (simple command), "medium" (multi-step), "high" (creative/complex).
9. Suggest how many tasks can run concurrently in suggested_parallelism.
10. Return ONLY JSON. No other text.
Structure: {{ "tasks": [ {{ "description": "...", "assigned_agent_role": "...", "depends_on": [0, 1], "priority": 1, "estimated_complexity": "medium" }} ], "suggested_parallelism": 2 }}"""

        for attempt in range(self.max_retries):
            try:
                response = await acompletion(model=self.model_name, messages=[{"role": "user", "content": prompt}])
                cleaned = self._repair_json(response.choices[0].message.content)
                plan_dict = json.loads(cleaned)
                plan = MissionPlan(**plan_dict)
                # Validate all roles exist
                valid_roles = set(a.role for a in self.active_agents.values())
                invalid = [t for t in plan.tasks if t.assigned_agent_role not in valid_roles]
                if invalid:
                    raise ValueError(f"Invalid roles: {[t.assigned_agent_role for t in invalid]}. Must use: {valid_roles}")
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

    async def run_mission(self, goal: str, uploaded_files_json: Optional[str] = None):
        mission_id = await create_mission(goal, uploaded_files_json)

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
                            if not is_safe_path(os.path.join("workspace", "uploads"), src):
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

        try:
            await self.recruit_squad(enriched_goal)

            # Inject shared branch into all agents
            for agent in self.active_agents.values():
                agent.active_branch = shared_branch

            plan = await self.plan_mission(enriched_goal)
            tasks = plan.tasks
            for i, t in enumerate(tasks):
                deps = f" (depends on: {t.depends_on})" if t.depends_on else ""
                print(f"  📝 Task {i}: [{t.assigned_agent_role}] {t.description}{deps}")
        except Exception as e:
            print(f"❌ [Manager]: Setup failed: {e}")
            await update_mission(mission_id, "FAILED")
            return

        # --- DAG-BASED PARALLEL EXECUTION ---
        task_states = {}  # task_idx -> "PENDING" | "RUNNING" | "COMPLETED" | "FAILED"
        task_results = {}  # task_idx -> output_text
        task_ids = {}  # task_idx -> database task_id
        
        for i in range(len(tasks)):
            task_states[i] = "PENDING"
        
        async def execute_task(task_idx: int, context: str) -> bool:
            """Execute a single task. Returns True if successful."""
            task_data = tasks[task_idx]
            agent = self.active_agents.get(task_data.assigned_agent_role)
            
            # Initialize agent metrics if not present
            if task_data.assigned_agent_role not in self.agent_metrics:
                self.agent_metrics[task_data.assigned_agent_role] = {
                    "tasks_completed": 0,
                    "tasks_failed": 0,
                    "total_time": 0.0
                }
            
            # Track load
            self.agent_load[task_data.assigned_agent_role] = self.agent_load.get(task_data.assigned_agent_role, 0) + 1
            
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
                self.agent_metrics[task_data.assigned_agent_role]["tasks_failed"] += 1
                self.agent_load[task_data.assigned_agent_role] -= 1
                health_monitor.record_failure(task_data.assigned_agent_role, "Agent role not found in active agents")
                return False
            
            print(f"\n🚀 [Manager]: Task {task_idx}/{len(tasks)} -> {agent.role}")
            task_id = await create_task(mission_id, task_data.description, agent.role)
            task_ids[task_idx] = task_id
            
            start_time = datetime.now()
            result = await agent.execute_task(task_data.description, context)
            elapsed = (datetime.now() - start_time).total_seconds()
            
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
        
        # Build dependency graph and execute in waves
        max_waves = len(tasks) * 2  # Safety limit
        wave = 0
        _memory_written = False
        
        while any(state == "PENDING" for state in task_states.values()) and wave < max_waves:
            wave += 1
            
            # Find tasks that are ready to execute (all dependencies completed)
            ready_tasks = []
            for i in range(len(tasks)):
                if task_states[i] != "PENDING":
                    continue
                
                # Check if all dependencies are completed
                deps = tasks[i].depends_on
                if all(task_states.get(dep) == "COMPLETED" for dep in deps):
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
            max_concurrent = getattr(plan, 'suggested_parallelism', 2)
            # Check if any agent is overloaded
            for task_idx in ready_tasks:
                role = tasks[task_idx].assigned_agent_role
                current_load = self.agent_load.get(role, 0)
                if current_load >= max_concurrent:
                    print(f"⚠️ [Manager]: Agent '{role}' is at capacity ({current_load} tasks). Deferring task {task_idx}.")
            
            # Execute in parallel (all ready tasks, load tracking happens inside execute_task)
            results = await asyncio.gather(
                *[execute_task(idx, task_contexts[idx]) for idx in ready_tasks],
                return_exceptions=True
            )
            
            # Handle exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    task_idx = ready_tasks[i]
                    print(f"❌ [Manager]: Task {task_idx} failed with exception: {result}")
                    task_states[task_idx] = "FAILED"
                    if task_idx in task_ids:
                        await update_task(task_ids[task_idx], status="FAILED", output_data=str(result))
                    if tasks[task_idx].assigned_agent_role in self.agent_metrics:
                        self.agent_metrics[tasks[task_idx].assigned_agent_role]["tasks_failed"] += 1
                    health_monitor.record_failure(tasks[task_idx].assigned_agent_role, str(result))
        
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
                    success = await execute_task(task_idx, new_context)
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
        
        # Agent performance report
        print(f"\n📊 [Manager]: Agent Performance Report:")
        for role, metrics in self.agent_metrics.items():
            total = metrics["tasks_completed"] + metrics["tasks_failed"]
            if total > 0:
                avg_time = metrics["total_time"] / max(1, metrics["tasks_completed"])
                success_rate = (metrics["tasks_completed"] / total) * 100
                print(f"   {role}: {metrics['tasks_completed']}/{total} succeeded ({success_rate:.0f}%), avg {avg_time:.1f}s/task")
        
        if failed > 0:
            print(f"\n⚠️ [Manager]: Mission #{mission_id} completed with {failed} failed task(s).")
            await update_mission(mission_id, "COMPLETED")
        else:
            print(f"\n✨ [Manager]: Mission #{mission_id} finished successfully ({completed} tasks completed in {wave} waves).")
            await update_mission(mission_id, "COMPLETED")