import os
import json
import time
from typing import Any, Dict, List, Optional
from litellm import acompletion, completion_cost
from ..tools.base import BaseTool
from ..utils.parser import extract_tool_calls_from_text

class BaseAgent:
    def __init__(
        self,
        role: str,
        goal: str,
        backstory: str,
        tools: List[BaseTool] = None,
        model_name: str = "gpt-4o-mini",
        model_override: Optional[str] = None
    ):
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.tools = tools or []

        # Local AI support
        local_mode = os.getenv("LOCAL_AI_MODE", "false").lower() == "true"
        default_local_model = "ollama/llama3"

        if model_override:
            self.model_name = model_override
        elif local_mode:
            self.model_name = default_local_model
        else:
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
            # Prepare acompletion arguments
            completion_kwargs = {
                "model": self.model_name,
                "messages": messages,
                "tools": litellm_tools if litellm_tools else None,
                "tool_choice": "auto" if litellm_tools else None
            }

            # Handle Ollama connection for local mode
            if self.model_name.startswith("ollama/"):
                completion_kwargs["api_base"] = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")

            # Reasoning loop (simple 1-turn tool-calling for now, could be expanded to a loop)
            response = await acompletion(**completion_kwargs)

            message = response.choices[0].message
            prompt_tokens = getattr(response.usage, 'prompt_tokens', 0)
            completion_tokens = getattr(response.usage, 'completion_tokens', 0)
            try:
                total_cost = completion_cost(completion_response=response)
            except:
                total_cost = 0.0

            # Fallback tool-calling parser for local models
            tool_calls = message.tool_calls
            if not tool_calls and message.content and litellm_tools:
                parsed_calls = extract_tool_calls_from_text(message.content)
                if parsed_calls:
                    # Simulate tool_calls structure
                    from types import SimpleNamespace
                    tool_calls = [
                        SimpleNamespace(
                            id=tc["id"],
                            function=SimpleNamespace(
                                name=tc["function"]["name"],
                                arguments=tc["function"]["arguments"]
                            )
                        )
                        for tc in parsed_calls
                    ]

            if tool_calls:
                # Execute tools and follow up
                # If we parsed them ourselves, we still need to add the assistant message
                if not message.tool_calls:
                    # Convert SimpleNamespace tool calls back to dict for message history
                    formatted_tool_calls = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in tool_calls
                    ]
                    messages.append({
                        "role": "assistant",
                        "content": message.content,
                        "tool_calls": formatted_tool_calls
                    })
                else:
                    messages.append(message)

                for tool_call in tool_calls:
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
                final_completion_kwargs = {
                    "model": self.model_name,
                    "messages": messages
                }
                if self.model_name.startswith("ollama/"):
                    final_completion_kwargs["api_base"] = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")

                response = await acompletion(**final_completion_kwargs)
                message = response.choices[0].message
                prompt_tokens += getattr(response.usage, 'prompt_tokens', 0)
                completion_tokens += getattr(response.usage, 'completion_tokens', 0)
                try:
                    total_cost += completion_cost(completion_response=response)
                except:
                    pass

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
