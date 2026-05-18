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
from squad_os.database.session import create_mission, create_task, update_task, update_mission, update_blackboard, get_pending_interrupt, update_interrupt_guidance, get_mission_budget, DB_PATH
from squad_os.core.projects import ProjectBranch
from squad_os.core.exceptions import AgentInterruptException, ToolRiskException
from squad_os.core.snapshot import capture_snapshot, restore_snapshot
from squad_os.core.circuit_breaker import QualityCircuitBreaker, validate_output_quality
from squad_os.core.context import ContextManager
from squad_os.core.logging import get_logger, Timer

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

    async def recruit_squad(self, goal: str, log):
        low_complexity_keywords = ["hi", "hello", "hey", "who are you", "what's up"]
        if goal.lower().strip() in low_complexity_keywords:
            log.info("Simple greeting detected, minimizing squad")
            self.active_agents = {
                "Assistant": BaseAgent(
                    role="Assistant",
                    goal="Respond politely to the user.",
                    backstory="A helpful and concise assistant.",
                    tools=[],
                    model_name=self.model_name
                )
            }
            return

        log.info("Analyzing job description and hiring specialists")
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
                    log.info("Hired specialist", role=member['role'])
                    self.active_agents[member['role']] = BaseAgent(
                        role=member['role'], goal=member['goal'], backstory=member['backstory'],
                        tools=assigned, model_name=self.model_name
                    )
                return
            except Exception as e:
                log.warning("Hiring JSON error, retrying", attempt=attempt+1, max_retries=self.max_retries, error=str(e))

        raise ValueError("Failed to parse Hiring JSON after max retries.")

    async def plan_mission(self, goal: str, log) -> MissionPlan:
        log.info("Planning execution strategy")
        roles = ", ".join([f"{a.role}" for a in self.active_agents.values()])

        prompt = f"""Mission: {goal}
Roles: {roles}

RULES FOR PLANNING:
1. Every task 'description' MUST specify which TOOL the agent should use.
2. If the agent needs to hire someone, the description MUST explicitly say: 'MUST use delegate_task'.
3. The LAST task MUST be assigned to one of the HIRED roles listed above and MUST explicitly say: 'MUST use commit_project tool to commit all artifacts'. Do NOT invent new roles not in the hired list.
4. Return ONLY JSON. No other text.
Structure: {{ "tasks": [ {{ "description": "...", "assigned_agent_role": "..." }} ] }}"""

        for attempt in range(self.max_retries):
            try:
                response = await acompletion(model=self.model_name, messages=[{"role": "user", "content": prompt}])
                cleaned = self._repair_json(response.choices[0].message.content)
                plan_dict = json.loads(cleaned)
                return MissionPlan(**plan_dict)
            except Exception as e:
                log.warning("Planning JSON error, retrying", attempt=attempt+1, max_retries=self.max_retries, error=str(e))

        # --- FATAL FALLBACK ---
        log.warning("LLM failed to plan, falling back to auto-generated sequential plan")
        fallback_tasks = []
        for role in self.active_agents.keys():
            fallback_tasks.append(TaskPlan(description=f"Execute your assigned goal: {self.active_agents[role].goal}", assigned_agent_role=role))
        return MissionPlan(tasks=fallback_tasks)

    async def run_mission(
        self,
        goal: str,
        uploaded_files_json: Optional[str] = None,
        max_tokens: int = 0,
        max_turns: int = 0,
        max_cost_usd: float = 0.0,
    ):
        mission_id = await create_mission(
            goal, uploaded_files_json,
            max_tokens=max_tokens, max_turns=max_turns, max_cost_usd=max_cost_usd,
        )
        log = get_logger("squad_os.manager", mission_id=mission_id)
        log.info("Mission started", goal=goal[:100], max_tokens=max_tokens, max_turns=max_turns, max_cost_usd=max_cost_usd)

        # 1. Create a Shared Project Branch for the Mission
        slug = goal[:30]
        branch_id = ProjectBranch.create_id(slug)
        shared_branch = ProjectBranch(branch_id)
        shared_branch.fork()
        log.info("Created shared mission branch", branch_id=branch_id)

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
                log.warning("Error processing uploaded files", error=str(e))

        try:
            await self.recruit_squad(enriched_goal, log)

            # Inject shared branch into all agents
            for agent in self.active_agents.values():
                agent.active_branch = shared_branch

            plan = await self.plan_mission(enriched_goal, log)
            tasks = plan.tasks
            for i, t in enumerate(tasks):
                log.info("Planned task", task_index=i+1, total=len(tasks), role=t.assigned_agent_role, description=t.description[:80])
        except Exception as e:
            log.error("Setup failed", error=str(e))
            await update_mission(mission_id, "FAILED")
            return

        context = ""
        task_idx = 0
        backtrack_counts = {}
        total_iteration_count = 0
        max_total_iterations = len(tasks) * 3
        quality_cb = QualityCircuitBreaker(failure_threshold=3)

        # Budget tracking
        cumulative_prompt_tokens = 0
        cumulative_completion_tokens = 0
        turn_count = 0

        # Context management — prevents context window overflow
        mission_ctx = ContextManager(
            max_history_turns=5,
            max_messages=20,
        )

        # Load budget from DB (supports resume with updated limits)
        budget = await get_mission_budget(mission_id)
        effective_max_tokens = max_tokens or (budget.get("max_tokens", 0) if budget else 0)
        effective_max_turns = max_turns or (budget.get("max_turns", 0) if budget else 0)
        effective_max_cost = max_cost_usd or (budget.get("max_cost_usd", 0.0) if budget else 0.0)

        interrupt = await get_pending_interrupt(mission_id)
        if interrupt and interrupt.get("user_guidance"):
            try:
                snapshot = await restore_snapshot(interrupt["id"])
                task_idx = snapshot.current_step_index
                context = snapshot.short_term_memory
                backtrack_counts = snapshot.backtrack_counts
                total_iteration_count = snapshot.total_iteration_count
                tasks = [
                    TaskPlan(description=t.description, assigned_agent_role=t.assigned_agent_role)
                    for t in snapshot.execution_plan
                ]
                context += f"\n\n### HUMAN OPERATOR GUIDANCE: {interrupt['user_guidance']}"
                cumulative_prompt_tokens = snapshot.prompt_tokens
                cumulative_completion_tokens = snapshot.completion_tokens
                turn_count = snapshot.total_iteration_count

                # Restore context summary from snapshot
                if snapshot.context_summary:
                    mission_ctx.summary = snapshot.context_summary

                # Reload budget in case it was topped up during pause
                budget = await get_mission_budget(mission_id)
                if budget:
                    effective_max_tokens = effective_max_tokens or budget.get("max_tokens", 0)
                    effective_max_turns = effective_max_turns or budget.get("max_turns", 0)
                    effective_max_cost = effective_max_cost or budget.get("max_cost_usd", 0.0)

                await update_interrupt_guidance(interrupt["id"], interrupt["user_guidance"])
                log.info("Resumed from interrupt", task_idx=task_idx+1)
            except Exception as e:
                log.error("Failed to restore snapshot", error=str(e))
                await update_mission(mission_id, "FAILED")
                return

        while task_idx < len(tasks):
            # Global iteration cap to prevent infinite loops
            total_iteration_count += 1
            if total_iteration_count > max_total_iterations:
                log.error("Maximum iteration count exceeded", max_iterations=max_total_iterations)
                await update_mission(mission_id, "FAILED")
                return

            # Budget check before each turn
            current_task_desc = tasks[task_idx].description if task_idx < len(tasks) else ""
            current_agent_role = self.active_agents.get(tasks[task_idx].assigned_agent_role)
            if effective_max_turns > 0 and turn_count >= effective_max_turns:
                log.warning("Turn budget exhausted", turn_count=turn_count, max_turns=effective_max_turns)
                await capture_snapshot(
                    mission_id=mission_id, goal=goal, plan_tasks=tasks,
                    task_idx=task_idx, current_task_desc=current_task_desc,
                    agent_role=current_agent_role.role if current_agent_role else "Unknown", messages=[],
                    context=context, backtrack_counts=backtrack_counts,
                    total_iterations=total_iteration_count,
                    reason="Budget Exhausted: Turn limit reached",
                    error_message=f"Turn budget: {turn_count}/{effective_max_turns}. Tokens used: {cumulative_prompt_tokens + cumulative_completion_tokens}",
                    prompt_tokens=cumulative_prompt_tokens,
                    completion_tokens=cumulative_completion_tokens,
                    max_tokens=effective_max_tokens,
                    max_turns=effective_max_turns,
                    max_cost_usd=effective_max_cost,
                    budget_exhausted=True,
                    context_summary=mission_ctx.summary,
                )
                await update_mission(mission_id, "PAUSED")
                return

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
                log.warning("Skipping task, role not found", role=task_data.assigned_agent_role)
                task_idx += 1
                continue

            task_id = await create_task(mission_id, task_data.description, agent.role)
            task_log = log.bind(task_id=task_id, agent_role=agent.role)
            task_log.info("Starting task", task_index=task_idx+1, total_tasks=len(tasks))

            try:
                # Build context with pruning — prevents unbounded growth
                effective_context = mission_ctx.get_context_with_summary(context)
                result = await agent.execute_task(task_data.description, effective_context, context_manager=mission_ctx)
            except AgentInterruptException as e:
                task_log.info("Agent requested human input", reason=e.reason)
                await capture_snapshot(
                    mission_id=mission_id, goal=goal, plan_tasks=tasks,
                    task_idx=task_idx, current_task_desc=task_data.description,
                    agent_role=agent.role, messages=e.messages,
                    context=context, backtrack_counts=backtrack_counts,
                    total_iterations=total_iteration_count, reason=e.reason,
                    prompt_tokens=cumulative_prompt_tokens + e.prompt_tokens,
                    completion_tokens=cumulative_completion_tokens + e.completion_tokens,
                    max_tokens=effective_max_tokens,
                    max_turns=effective_max_turns,
                    max_cost_usd=effective_max_cost,
                    context_summary=mission_ctx.summary,
                )
                await update_mission(mission_id, "PAUSED")
                log.info("Mission paused for HITL review")
                return
            except ToolRiskException as e:
                task_log.warning("High-risk tool blocked", tool=e.tool_name, risk_tier=e.risk_tier, risk_label=e.risk_label)
                await capture_snapshot(
                    mission_id=mission_id, goal=goal, plan_tasks=tasks,
                    task_idx=task_idx, current_task_desc=task_data.description,
                    agent_role=agent.role, messages=e.messages,
                    context=context, backtrack_counts=backtrack_counts,
                    total_iterations=total_iteration_count,
                    reason=f"Tool approval required: {e.tool_name} (Tier {e.risk_tier}: {e.risk_label})",
                    error_message=json.dumps(e.tool_args),
                    prompt_tokens=cumulative_prompt_tokens + e.prompt_tokens,
                    completion_tokens=cumulative_completion_tokens + e.completion_tokens,
                    max_tokens=effective_max_tokens,
                    max_turns=effective_max_turns,
                    max_cost_usd=effective_max_cost,
                    context_summary=mission_ctx.summary,
                )
                await update_mission(mission_id, "PAUSED")
                log.info("Mission paused for tool approval")
                return

            # Update budget tracking from this turn
            turn_tokens_prompt = result.get("prompt_tokens", 0)
            turn_tokens_completion = result.get("completion_tokens", 0)
            cumulative_prompt_tokens += turn_tokens_prompt
            cumulative_completion_tokens += turn_tokens_completion
            turn_count += 1

            # Update context summary from agent execution
            if result.get("context_summary"):
                mission_ctx.summary = result["context_summary"]

            # Check token budget after the turn
            total_tokens = cumulative_prompt_tokens + cumulative_completion_tokens
            if effective_max_tokens > 0 and total_tokens > effective_max_tokens:
                task_log.warning("Token budget exhausted", total_tokens=total_tokens, max_tokens=effective_max_tokens)
                output_text = result.get("output", "Task completed without text summary.")
                await capture_snapshot(
                    mission_id=mission_id, goal=goal, plan_tasks=tasks,
                    task_idx=task_idx, current_task_desc=task_data.description,
                    agent_role=agent.role, messages=[],
                    context=context, backtrack_counts=backtrack_counts,
                    total_iterations=total_iteration_count,
                    reason="Budget Exhausted: Token limit reached",
                    error_message=f"Token budget: {total_tokens}/{effective_max_tokens} (prompt: {cumulative_prompt_tokens}, completion: {cumulative_completion_tokens})",
                    prompt_tokens=cumulative_prompt_tokens,
                    completion_tokens=cumulative_completion_tokens,
                    max_tokens=effective_max_tokens,
                    max_turns=effective_max_turns,
                    max_cost_usd=effective_max_cost,
                    budget_exhausted=True,
                    context_summary=mission_ctx.summary,
                )
                await update_mission(mission_id, "PAUSED")
                return

            output_text = result.get("output", "Task completed without text summary.")

            is_valid, quality_reason = validate_output_quality(output_text)
            if not is_valid:
                failure_count = quality_cb.record_failure(task_id)
                task_log.warning("Quality failure", reason=quality_reason, failure_count=failure_count, threshold=quality_cb.failure_threshold)
                if quality_cb.is_open(task_id):
                    task_log.warning("Quality circuit opened, pausing for human review", failure_count=failure_count)
                    await capture_snapshot(
                        mission_id=mission_id, goal=goal, plan_tasks=tasks,
                        task_idx=task_idx, current_task_desc=task_data.description,
                        agent_role=agent.role, messages=[],
                        context=context, backtrack_counts=backtrack_counts,
                        total_iterations=total_iteration_count,
                        reason="Output quality circuit opened",
                        error_message=f"Consecutive failures ({failure_count}): {quality_reason}. Raw output: {output_text[:500]}",
                        quality_failure_count=failure_count,
                        prompt_tokens=cumulative_prompt_tokens,
                        completion_tokens=cumulative_completion_tokens,
                        max_tokens=effective_max_tokens,
                        max_turns=effective_max_turns,
                        max_cost_usd=effective_max_cost,
                        context_summary=mission_ctx.summary,
                    )
                    await update_mission(mission_id, "PAUSED")
                    log.info("Mission paused for quality review")
                    return
                context += f"\n\nQUALITY ERROR: {quality_reason}. Please regenerate with better output."
                continue
            else:
                quality_cb.record_success(task_id)

            # --- TOOL ENFORCEMENT CHECK ---
            must_use = "must use" in task_data.description.lower() or "delegate_task" in task_data.description.lower()
            if must_use and len(output_text) < 20 and "DELEGATED" not in output_text:
                task_log.warning("Agent skipped mandatory tool use, forcing retry")
                context += f"\n\nERROR: You skipped a mandatory tool call. You MUST execute the tool now."
                continue

            # --- QA CHECK ---
            if "qa" in agent.role.lower() and any(w in output_text.lower() for w in ["fail", "reject", "error"]):
                backtrack_counts[task_idx] = backtrack_counts.get(task_idx, 0) + 1
                if backtrack_counts[task_idx] <= self.max_retries:
                    task_log.info("QA failure detected, sending previous agent back", attempt=backtrack_counts[task_idx], max_retries=self.max_retries)
                    context += f"\n\n### QA FEEDBACK: {output_text}"
                    task_idx = max(0, task_idx - 1)
                    continue
                else:
                    task_log.warning("QA backtrack limit exceeded, proceeding anyway")
                    backtrack_counts[task_idx] = 0

            # Success path
            await update_task(task_id, status="COMPLETED", output_data=output_text)
            context += f"\n\nResult from {agent.role}: {output_text}"
            task_idx += 1

        await update_mission(mission_id, "COMPLETED")
        log.info("Mission finished successfully", total_tasks=len(tasks), total_tokens=cumulative_prompt_tokens + cumulative_completion_tokens, total_turns=turn_count)