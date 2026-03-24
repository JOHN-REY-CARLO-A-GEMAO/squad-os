import os
import json
import time
from typing import Any, Dict, List, Optional
from litellm import acompletion, completion_cost
from ..tools.base import BaseTool
from ..utils.parser import extract_tool_calls_from_text
from ..utils.dashboard import dashboard
from ..database.session import get_relevant_post_mortems

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

    async def execute_task(self, task_description: str, context: str = "", max_turns: int = 10) -> Dict[str, Any]:
        start_time = time.time()
        
        # Retrieve relevant post-mortems for long-term memory
        past_experiences = await get_relevant_post_mortems(task_description)
        memory_context = ""
        if past_experiences:
            memory_context = "\nRelevant past experiences:\n" + "\n".join([
                f"- Goal: {m['goal']}\n  Outcome: {m['outcome'][:200]}..."
                for m in past_experiences
            ])

        tool_descriptions = "\n".join([f"- {t.name}: {t.description} (Args: {json.dumps(t.parameters)})" for t in self.tools])

        system_prompt = f"""You are {self.role}.
Your goal is: {self.goal}
Your backstory: {self.backstory}

To complete your task, you can think and use tools.
Wrap your internal reasoning in <thought> tags.
To call a tool, use XML format: <call:tool_name>{{"arg1": "value1"}}</call:tool_name>
The system will respond with <response>tool result</response>.
Continue this loop until you have the final answer.
When you are ready to provide the final output, simply write it without any tags.

Available tools:
{tool_descriptions}
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context: {context}\n{memory_context}\n\nTask: {task_description}"}
        ]

        prompt_tokens = 0
        completion_tokens = 0
        total_cost = 0.0
        turn_count = 0

        try:
            while turn_count < max_turns:
                turn_count += 1

                completion_kwargs = {
                    "model": self.model_name,
                    "messages": messages,
                }

                if self.model_name.startswith("ollama/"):
                    completion_kwargs["api_base"] = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
                else:
                    # For cloud models, we can still provide tools in the standard way
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
                    if litellm_tools:
                        completion_kwargs["tools"] = litellm_tools
                        completion_kwargs["tool_choice"] = "auto"

                response = await acompletion(**completion_kwargs)
                message = response.choices[0].message

                prompt_tokens += getattr(response.usage, 'prompt_tokens', 0)
                completion_tokens += getattr(response.usage, 'completion_tokens', 0)
                try:
                    total_cost += completion_cost(completion_response=response)
                except:
                    pass

                # Add assistant message to history
                messages.append(message)

                # Log thinking if present
                if "<thought>" in (message.content or ""):
                    import re
                    thought = re.search(r"<thought>(.*?)</thought>", message.content, re.DOTALL)
                    if thought:
                        dashboard.log_thought(self.role, thought.group(1).strip())

                # Parse tool calls (both native and XML)
                tool_calls = message.tool_calls or []
                if not tool_calls and message.content:
                    parsed_calls = extract_tool_calls_from_text(message.content)
                    if parsed_calls:
                        from types import SimpleNamespace
                        tool_calls = [
                            SimpleNamespace(
                                id=tc.get("id", f"call_{time.time()}"),
                                function=SimpleNamespace(
                                    name=tc["function"]["name"],
                                    arguments=tc["function"]["arguments"]
                                )
                            )
                            for tc in parsed_calls
                        ]

                if not tool_calls:
                    # No tool calls, assume final answer
                    break

                # Execute tool calls
                for tool_call in tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        tool_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        tool_args = {"input": tool_call.function.arguments}
                    
                    dashboard.log_tool_call(self.role, tool_name, json.dumps(tool_args))

                    tool = next((t for t in self.tools if t.name == tool_name), None)
                    if tool:
                        try:
                            result = await tool.execute(**tool_args)
                            tool_msg = {
                                "role": "tool" if not self.model_name.startswith("ollama/") else "user",
                                "name": tool_name,
                                "tool_call_id": tool_call.id,
                                "content": f"<response>{result}</response>"
                            }
                            # For some models, 'name' and 'tool_call_id' aren't allowed in 'user' role
                            if self.model_name.startswith("ollama/"):
                                tool_msg = {"role": "user", "content": f"Tool {tool_name} returned: {result}"}

                            messages.append(tool_msg)
                        except Exception as e:
                            error_msg = f"Error executing tool {tool_name}: {str(e)}"
                            messages.append({
                                "role": "user",
                                "content": f"System: {error_msg}. Please correct your tool call."
                            })
                    else:
                        messages.append({
                            "role": "user",
                            "content": f"System: Tool {tool_name} not found. Available tools: {[t.name for t in self.tools]}"
                        })

            execution_ms = int((time.time() - start_time) * 1000)
            
            last_message = messages[-1]
            if isinstance(last_message, dict):
                output = last_message.get("content", "")
            else:
                output = getattr(last_message, "content", "")

            return {
                "output": output,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost_usd": total_cost,
                "execution_ms": execution_ms,
                "turns": turn_count
            }

        except Exception as e:
            return {
                "error": str(e),
                "execution_ms": int((time.time() - start_time) * 1000)
            }
