import os
import json
import asyncio
from typing import Any, Dict, List, Optional
import litellm
from squad_os.tools.base import BaseTool

class BaseAgent:
    def __init__(self, role: str, goal: str, backstory: str, tools: List[BaseTool] = None, model_name: str = "gpt-4o-mini"):
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.model_name = model_name
        self.tools = {t.name: t for t in (tools or [])}

    async def execute_task(self, task_description: str, context: str) -> Dict[str, Any]:
        tool_schemas = [{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}} for t in self.tools.values()]
        messages = [
            {"role": "system", "content": f"You are {self.role}. {self.backstory}\nGoal: {self.goal}"},
            {"role": "user", "content": f"Context: {context}\n\nTask: {task_description}\n\nIMPORTANT: Use tools to find info. Provide a final written summary."}
        ]
        for _ in range(5):
            response = await litellm.acompletion(model=self.model_name, messages=messages, tools=tool_schemas if tool_schemas else None)
            resp_msg = response.choices[0].message
            messages.append(resp_msg)
            if resp_msg.get("tool_calls"):
                for tool_call in resp_msg["tool_calls"]:
                    t_name = tool_call.function.name
                    t_args = json.loads(tool_call.function.arguments)
                    if t_name in self.tools:
                        print(f"  [{self.role}] calling {t_name}...")
                        result = await self.tools[t_name].execute(**t_args)
                        messages.append({"role": "tool", "name": t_name, "tool_call_id": tool_call.id, "content": str(result)})
                continue 
            return {"output": resp_msg.content, "prompt_tokens": response.usage.prompt_tokens, "completion_tokens": response.usage.completion_tokens}
        return {"output": "Max reasoning steps reached.", "error": "Loop timeout"}
