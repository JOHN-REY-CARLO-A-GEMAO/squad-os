import os
import json
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from litellm import acompletion
import asyncio
from ..agents.base import BaseAgent
from ..database.session import (
    create_mission,
    create_task,
    update_task,
    update_mission,
    get_mission_tasks,
    create_post_mortem
)
from ..utils.dashboard import dashboard
from rich.live import Live

class TaskPlan(BaseModel):
    task_id: str = Field(description="Unique identifier for the task (e.g., 'task_1')")
    description: str = Field(description="Detailed instruction for the agent")
    assigned_agent_role: str = Field(description="The exact role of the agent to assign this to")
    depends_on: List[str] = Field(default_factory=list, description="List of task_ids that must be completed before this task starts")

class MissionPlan(BaseModel):
    tasks: List[TaskPlan] = Field(description="Sequential list of tasks to achieve the goal")

class Manager:
    def __init__(self, agents: List[BaseAgent], model_name: str = "gpt-4o-mini"):
        self.agents = {agent.role: agent for agent in agents}

        # Local AI support
        local_mode = os.getenv("LOCAL_AI_MODE", "false").lower() == "true"
        default_local_model = "ollama/llama3"

        if local_mode:
            self.model_name = default_local_model
        else:
            self.model_name = model_name

        self.max_retries = 3

    async def plan_mission(self, goal: str) -> MissionPlan:
        agent_descriptions = "\n".join([f"- {a.role}: {a.goal}" for a in self.agents.values()])
        
        system_prompt = f"""You are a Lead Systems Architect. 
Your goal is to break down a high-level mission into a series of tasks.
Tasks can run in parallel if they don't depend on each other.
Use the 'depends_on' field to specify task dependencies using 'task_id'.

Assign each task to the most appropriate agent from the following list:
{agent_descriptions}

Return your response as a structured JSON object representing the MissionPlan.
"""
        completion_kwargs = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"The mission goal is: {goal}"}
            ],
            "response_format": {"type": "json_object", "schema": MissionPlan.model_json_schema()}
        }

        if self.model_name.startswith("ollama/"):
            completion_kwargs["api_base"] = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
            # Local models might not support response_format="json_object" well,
            # but LiteLLM handles it for some. We'll keep it and hope for the best,
            # or could add a fallback if needed.

        response = await acompletion(**completion_kwargs)
        
        plan_data = json.loads(response.choices[0].message.content)
        return MissionPlan(**plan_data)

    async def run_mission(self, goal: str):
        mission_id = await create_mission(goal)
        dashboard.update_header(goal)
        
        with Live(dashboard.get_layout(), refresh_per_second=4, console=dashboard.console) as live:
            plan = await self.plan_mission(goal)

            task_results = {} # task_id -> output
            completed_tasks = set()
            failed_tasks = set()
            
            # Helper to get context from dependencies
            def get_context(depends_on: List[str]) -> str:
                context_parts = []
                for dep_id in depends_on:
                    if dep_id in task_results:
                        context_parts.append(f"Output from {dep_id}:\n{task_results[dep_id]}")
                return "\n\n".join(context_parts)

            async def run_task(task_plan: TaskPlan):
                agent = self.agents.get(task_plan.assigned_agent_role)
                if not agent:
                    logging.error(f"Agent with role {task_plan.assigned_agent_role} not found.")
                    return None

                db_task_id = await create_task(mission_id, task_plan.description, agent.role, task_name=task_plan.task_id)
                dashboard.log_status(agent.role, f"Waiting for dependencies: {task_plan.depends_on}")

                # Wait for dependencies or failure
                for dep_id in task_plan.depends_on:
                    while dep_id not in completed_tasks:
                        if dep_id in failed_tasks:
                            dashboard.log_status(agent.role, f"Dependency {dep_id} failed. Skipping task.")
                            await update_task(db_task_id, status="SKIPPED", error=f"Dependency {dep_id} failed.")
                            failed_tasks.add(task_plan.task_id)
                            task_results[task_plan.task_id] = f"SKIPPED: Dependency {dep_id} failed"
                            live.update(dashboard.get_layout())
                            return None
                        await asyncio.sleep(0.5)
                        live.update(dashboard.get_layout())
                
                context = get_context(task_plan.depends_on)
                dashboard.log_status(agent.role, f"Executing: {task_plan.task_id}")
                live.update(dashboard.get_layout())

                retry_count = 0
                while retry_count <= self.max_retries:
                    result = await agent.execute_task(task_plan.description, context)
                    live.update(dashboard.get_layout())

                    if "error" in result:
                        retry_count += 1
                        if retry_count > self.max_retries:
                            await update_task(db_task_id, status="FAILED", error=result["error"], retry_count=retry_count-1)
                            failed_tasks.add(task_plan.task_id)
                            task_results[task_plan.task_id] = f"FAILED: {result['error']}"
                            dashboard.log_status(agent.role, f"Failed: {task_plan.task_id}")
                            live.update(dashboard.get_layout())
                            return None
                        dashboard.log_status(agent.role, f"Error (Attempt {retry_count}): {result['error']}. Retrying...")
                        continue

                    # Successful execution
                    await update_task(
                        db_task_id,
                        status="COMPLETED",
                        output_data=result["output"],
                        prompt_tokens=result["prompt_tokens"],
                        completion_tokens=result["completion_tokens"],
                        cost_usd=result["cost_usd"],
                        execution_ms=result["execution_ms"],
                        retry_count=retry_count
                    )
                    task_results[task_plan.task_id] = result["output"]
                    completed_tasks.add(task_plan.task_id)
                    dashboard.log_status(agent.role, f"Completed: {task_plan.task_id}")
                    live.update(dashboard.get_layout())
                    return result["output"]

            # Dispatch all tasks; they will wait for their dependencies internally
            futures = [asyncio.create_task(run_task(tp)) for tp in plan.tasks]
            await asyncio.gather(*futures)

            # Generate post-mortem
            mission_outcome = "\n\n".join([f"Task {tid}: {res}" for tid, res in task_results.items()])
            all_tools_used = []
            for agent in self.agents.values():
                 all_tools_used.extend([t.name for t in agent.tools])

            await create_post_mortem(mission_id, goal, mission_outcome, list(set(all_tools_used)))
            await update_mission(mission_id, "COMPLETED")

            return mission_outcome
