import os
import json
import time
from typing import Any, Dict, List, Optional
from litellm import acompletion, completion_cost
from ..tools.base import BaseTool

class BaseAgent:
    def __init__(
        self,
        role: str,
        goal: str,
        backstory: str,
        tools: List[BaseTool] = None,
        model_name: str = "gpt-4o-mini"
    ):
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.tools = tools or []
        self.model_name = model_name

    async def execute_task(self, task_description: str, context: str = "") -> Dict[str, Any]:
        start_time = time.time()
        
        system_prompt = f"""You are {self.role}.
Your goal is: {self.goal}
Your backstory: {self.backstory}

Respond with only the final output for the task. Use your available tools if needed.
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context: {context}\n\nTask: {task_description}"}
        ]

        # Convert tool objects to LiteLLM format
        litellm_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            }
            for tool in self.tools
        ]

        try:
            # Reasoning loop (simple 1-turn tool-calling for now, could be expanded to a loop)
            response = await acompletion(
                model=self.model_name,
                messages=messages,
                tools=litellm_tools if litellm_tools else None,
                tool_choice="auto" if litellm_tools else None
            )

            message = response.choices[0].message
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            total_cost = completion_cost(completion_response=response)

            if message.tool_calls:
                # Execute tools and follow up
                messages.append(message)
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    tool = next((t for t in self.tools if t.name == tool_name), None)
                    if tool:
                        result = await tool.execute(**tool_args)
                        messages.append({
                            "role": "tool",
                            "name": tool_name,
                            "tool_call_id": tool_call.id,
                            "content": result
                        })
                    else:
                        messages.append({
                            "role": "tool",
                            "name": tool_name,
                            "tool_call_id": tool_call.id,
                            "content": f"Error: Tool {tool_name} not found."
                        })

                # Get final answer after tool use
                response = await acompletion(
                    model=self.model_name,
                    messages=messages
                )
                message = response.choices[0].message
                prompt_tokens += response.usage.prompt_tokens
                completion_tokens += response.usage.completion_tokens
                total_cost += completion_cost(completion_response=response)

            execution_ms = int((time.time() - start_time) * 1000)
            
            return {
                "output": message.content,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost_usd": total_cost,
                "execution_ms": execution_ms
            }

        except Exception as e:
            return {
                "error": str(e),
                "execution_ms": int((time.time() - start_time) * 1000)
            }
