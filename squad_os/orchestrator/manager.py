import os
import json
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from litellm import acompletion
from ..agents.base import BaseAgent
from ..database.session import create_mission, create_task, update_task, update_mission

class TaskPlan(BaseModel):
    description: str = Field(description="Detailed instruction for the agent")
    assigned_agent_role: str = Field(description="The exact role of the agent to assign this to")

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
Your goal is to break down a high-level mission into a series of sequential tasks.
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
        plan = await self.plan_mission(goal)
        
        context = ""
        for task_plan in plan.tasks:
            agent = self.agents.get(task_plan.assigned_agent_role)
            if not agent:
                logging.error(f"Agent with role {task_plan.assigned_agent_role} not found.")
                continue

            task_id = await create_task(mission_id, task_plan.description, agent.role)
            
            retry_count = 0
            while retry_count <= self.max_retries:
                result = await agent.execute_task(task_plan.description, context)
                
                if "error" in result:
                    await update_task(task_id, status="FAILED", error=result["error"], retry_count=retry_count)
                    break # Critical failure

                # QA/Reviewer Handoff & Loop Logic
                # Check for failure indications in a more robust way if possible
                is_failed = agent.role == "QA/Reviewer" and any(word in result["output"].lower() for word in ["error", "failed", "bug", "reject"])
                
                if is_failed:
                    retry_count += 1
                    if retry_count > self.max_retries:
                        await update_task(task_id, status="FAILED_REQUIRES_HUMAN_INTERVENTION", output_data=result["output"], retry_count=retry_count)
                        await update_mission(mission_id, "FAILED")
                        return

                    # Identify the agent responsible for the previous step (usually Developer)
                    # We look for the most recent successful task that wasn't QA
                    tasks = await get_mission_tasks(mission_id)
                    previous_dev_task = next((t for t in reversed(tasks) if t["status"] == "COMPLETED" and t["assigned_agent"] != "QA/Reviewer"), None)
                    
                    if previous_dev_task:
                        dev_agent_role = previous_dev_task["assigned_agent"]
                        dev_agent = self.agents.get(dev_agent_role)
                        if dev_agent:
                            feedback_context = f"QA Feedback: {result['output']}\n\nOriginal Task: {previous_dev_task['description']}"
                            logging.info(f"Retrying task through {dev_agent_role} due to QA failure. Attempt {retry_count}")
                            dev_result = await dev_agent.execute_task(f"Fix the issues found by QA in your previous task: {previous_dev_task['description']}", feedback_context)
                            context += f"\n\nRefined output from {dev_agent_role} (after QA feedback):\n{dev_result['output']}"
                            # Re-run QA agent with updated context
                            continue
                
                # Successful execution
                await update_task(
                    task_id, 
                    status="COMPLETED", 
                    output_data=result["output"], 
                    prompt_tokens=result["prompt_tokens"],
                    completion_tokens=result["completion_tokens"],
                    cost_usd=result["cost_usd"],
                    execution_ms=result["execution_ms"],
                    retry_count=retry_count
                )
                context += f"\n\nOutput from {agent.role}:\n{result['output']}"
                break # Exit retry loop on success

        await update_mission(mission_id, "COMPLETED")
        return context
