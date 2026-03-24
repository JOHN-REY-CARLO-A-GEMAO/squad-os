import json
import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from litellm import acompletion
from ..agents.base import BaseAgent
from ..database.session import create_mission, create_task, update_task, update_mission

# Schema for a single task
class TaskPlan(BaseModel):
    description: str = Field(description="Detailed instruction for the agent")
    assigned_agent_role: str = Field(description="The exact role of the agent to assign this to")

# Schema for the full mission
class MissionPlan(BaseModel):
    tasks: List[TaskPlan] = Field(description="Sequential list of tasks to achieve the goal")

class Manager:
    def __init__(self, agents: List[BaseAgent], model_name: str = "gpt-4o-mini"):
        # Map agents by their role for easy lookup
        self.agents = {agent.role: agent for agent in agents}
        self.model_name = model_name
        self.max_retries = 3

    async def plan_mission(self, goal: str) -> MissionPlan:
        """Asks the LLM to break the goal into a JSON list of tasks."""
        agent_descriptions = "\n".join([f"- {a.role}: {a.goal}" for a in self.agents.values()])
        
        system_prompt = f"""You are a Lead Systems Architect. 
Your goal is to break down a high-level mission into a series of sequential tasks.
Assign each task to the most appropriate agent from the following list:
{agent_descriptions}

IMPORTANT: Your response must be a valid JSON object. Do not include any intro or outro text.
JSON Structure:
{{
  "tasks": [
    {{ "description": "...", "assigned_agent_role": "..." }}
  ]
}}
"""
        # Call the model (Ollama or Cloud)
        response = await acompletion(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"The mission goal is: {goal}"}
            ],
            response_format={"type": "json_object"}
        )
        
        raw_content = response.choices[0].message.content.strip()

        # --- ROBUST JSON CLEANING ---
        if "```" in raw_content:
            raw_content = re.sub(r"```(?:json)?\s*(.*?)\s*```", r"\1", raw_content, flags=re.DOTALL)
        
        try:
            plan_dict = json.loads(raw_content)
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON from model. Raw content: {raw_content}")
            raise e

        if "mission" in plan_dict and "tasks" not in plan_dict:
            if isinstance(plan_dict["mission"], dict) and "tasks" in plan_dict["mission"]:
                plan_dict["tasks"] = plan_dict["mission"]["tasks"]
            elif isinstance(plan_dict["mission"], list):
                plan_dict["tasks"] = plan_dict["mission"]

        return MissionPlan(**plan_dict)

    async def run_mission(self, goal: str):
        """Executes the plan by handing tasks to agents one by one."""
        mission_id = await create_mission(goal)
        
        try:
            plan = await self.plan_mission(goal)
        except Exception as e:
            logging.error(f"Mission planning failed: {e}")
            await update_mission(mission_id, "FAILED")
            return f"Planning Error: {str(e)}"

        context = ""
        
        # Step 2: Execute each task in the plan
        for task_plan in plan.tasks:
            # --- START FUZZY MATCH FIX ---
            # 1. Try exact match first
            agent = self.agents.get(task_plan.assigned_agent_role)
            
            # 2. Try Fuzzy match if exact match fails
            if not agent:
                target_role = task_plan.assigned_agent_role.lower()
                for role_name, potential_agent in self.agents.items():
                    # Check if our role is inside the LLM's response
                    if role_name.lower() in target_role:
                        agent = potential_agent
                        logging.info(f"Fuzzy Matched '{task_plan.assigned_agent_role}' to '{role_name}'")
                        break
            # --- END FUZZY MATCH FIX ---

            if not agent:
                logging.warning(f"Agent role '{task_plan.assigned_agent_role}' not found. Skipping task.")
                continue

            # Create entry in DB
            task_id = await create_task(mission_id, task_plan.description, agent.role)
            logging.info(f"Starting Task: {task_plan.description} (Agent: {agent.role})")

            retry_count = 0
            while retry_count <= self.max_retries:
                result = await agent.execute_task(task_plan.description, context)
                
                if "error" in result:
                    logging.error(f"Agent {agent.role} failed: {result['error']}")
                    await update_task(task_id, status="FAILED", error=result["error"], retry_count=retry_count)
                    break 

                is_failed_qa = (agent.role == "QA/Reviewer" and 
                               any(word in result["output"].lower() for word in ["fail", "reject", "bug", "error"]))
                
                if is_failed_qa:
                    retry_count += 1
                    logging.warning(f"QA Rejected work. Retry attempt {retry_count}")
                    if retry_count > self.max_retries:
                        await update_task(task_id, status="FAILED_QA", output_data=result["output"])
                        await update_mission(mission_id, "FAILED")
                        return "Mission failed at QA stage."
                    continue 

                await update_task(
                    task_id, 
                    status="COMPLETED", 
                    output_data=result["output"], 
                    prompt_tokens=result.get("prompt_tokens", 0),
                    completion_tokens=result.get("completion_tokens", 0),
                    cost_usd=result.get("cost_usd", 0.0),
                    execution_ms=result.get("execution_ms", 0),
                    retry_count=retry_count
                )
                
                context += f"\n\n### Result from {agent.role}:\n{result['output']}"
                break 

        await update_mission(mission_id, "COMPLETED")
        return context