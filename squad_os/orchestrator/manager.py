import json
import logging
import re
import asyncio
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from litellm import acompletion
import os
import shutil
import aiosqlite
from squad_os.agents.base import BaseAgent
from squad_os.database.session import create_mission, create_task, update_task, update_mission, update_blackboard, DB_PATH
from squad_os.core.projects import ProjectBranch

class TaskPlan(BaseModel):
    description: str
    assigned_agent_role: str

class MissionPlan(BaseModel):
    tasks: List[TaskPlan]

class Manager:
    def __init__(self, tool_inventory: List[Any], model_name: str = "gpt-4o-mini"):
        self.tool_inventory = {t.name: t for t in tool_inventory}
        self.model_name = model_name
        self.max_retries = 3
        self.active_agents = {}

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
        if '"squad":' not in content and '"tasks":' not in content:
            content = content.replace("'", '"')
        return content

    async def recruit_squad(self, goal: str):
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
                commit_keywords = ["devops", "version control", "deployment", "release"]
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
Roles: {roles}

RULES FOR PLANNING:
1. Every task 'description' MUST specify which TOOL the agent should use.
2. If the agent needs to hire someone, the description MUST explicitly say: 'MUST use delegate_task'.
3. The LAST task MUST always be assigned to a DevOps/Version Control role and MUST explicitly say: 'MUST use commit_project tool to commit all artifacts'.
4. Return ONLY JSON. No other text.
Structure: {{ "tasks": [ {{ "description": "...", "assigned_agent_role": "..." }} ] }}"""

        for attempt in range(self.max_retries):
            try:
                response = await acompletion(model=self.model_name, messages=[{"role": "user", "content": prompt}])
                cleaned = self._repair_json(response.choices[0].message.content)
                plan_dict = json.loads(cleaned)
                return MissionPlan(**plan_dict)
            except Exception as e:
                print(f"🔄 [Manager]: Planning JSON Error. Retrying... ({attempt+1}/{self.max_retries})")

        # --- FATAL FALLBACK ---
        print("⚠️ [Manager]: LLM failed to plan. Falling back to an auto-generated sequential plan.")
        fallback_tasks = []
        for role in self.active_agents.keys():
            fallback_tasks.append(TaskPlan(description=f"Execute your assigned goal: {self.active_agents[role].goal}", assigned_agent_role=role))
        return MissionPlan(tasks=fallback_tasks)

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
                print(f"  📝 Task {i+1}: [{t.assigned_agent_role}] {t.description}")
        except Exception as e:
            print(f"❌ [Manager]: Setup failed: {e}")
            await update_mission(mission_id, "FAILED")
            return

        context = ""
        task_idx = 0
        backtrack_counts = {}

        while task_idx < len(tasks):
            task_data = tasks[task_idx]
            agent = self.active_agents.get(task_data.assigned_agent_role)

            # Fuzzy match fallback
            if not agent:
                target = str(task_data.assigned_agent_role).lower()
                for r, a in self.active_agents.items():
                    if r.lower() in target or target in r.lower():
                        agent = a
                        break

            if not agent:
                print(f"⚠️ [Manager]: Skipping task, role '{task_data.assigned_agent_role}' not found.")
                task_idx += 1
                continue

            print(f"\n🚀 [Manager]: Task {task_idx+1}/{len(tasks)} -> {agent.role}")
            task_id = await create_task(mission_id, task_data.description, agent.role)

            result = await agent.execute_task(task_data.description, context)
            output_text = result.get("output", "Task completed without text summary.")

            # --- TOOL ENFORCEMENT CHECK ---
            must_use = "must use" in task_data.description.lower() or "delegate_task" in task_data.description.lower()
            if must_use and len(output_text) < 20 and "DELEGATED" not in output_text:
                print(f"⚠️ [Manager]: Agent {agent.role} skipped mandatory tool use. Forcing retry...")
                context += f"\n\nERROR: You skipped a mandatory tool call. You MUST execute the tool now."
                continue

            # --- QA CHECK ---
            if "qa" in agent.role.lower() and any(w in output_text.lower() for w in ["fail", "reject", "error"]):
                backtrack_counts[task_idx] = backtrack_counts.get(task_idx, 0) + 1
                if backtrack_counts[task_idx] <= self.max_retries:
                    print(f"🔄 [Manager]: QA Failure detected. Sending previous agent back to fix it...")
                    context += f"\n\n### QA FEEDBACK: {output_text}"
                    task_idx = max(0, task_idx - 1)
                    continue

            # Success path
            await update_task(task_id, status="COMPLETED", output_data=output_text)
            context += f"\n\nResult from {agent.role}: {output_text}"
            task_idx += 1

        await update_mission(mission_id, "COMPLETED")
        print(f"\n✨ [Manager]: Mission #{mission_id} finished successfully.")