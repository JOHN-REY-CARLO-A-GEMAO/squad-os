import os
import json
import asyncio
from typing import Any, Dict, List, Optional
import litellm
from squad_os.tools.base import BaseTool
from squad_os.core.projects import ProjectBranch

class BaseAgent:
    def __init__(self, role: str, goal: str, backstory: str, tools: List[BaseTool] = None, model_name: str = "gpt-4o-mini", branch_id: str = None):
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.model_name = model_name
        self.tools = {t.name: t for t in (tools or [])}
        self.active_branch: Optional[ProjectBranch] = None
        if branch_id:
            self.active_branch = ProjectBranch(branch_id)

    async def execute_task(self, task_description: str, context: str) -> Dict[str, Any]:
        if not self.active_branch:
            branch_id = ProjectBranch.create_id(task_description[:30])
            self.active_branch = ProjectBranch(branch_id)
            self.active_branch.fork()
            print(f"🚀 [Fork]: Created new branch {branch_id}")

        # Update tools with active branch context
        for tool in self.tools.values():
            if hasattr(tool, "workspace") or hasattr(tool, "output_dir"):
                # We need a way to dynamically update tool paths
                if hasattr(tool, "workspace"):
                    tool.workspace = self.active_branch.project_path
                if hasattr(tool, "output_dir"):
                    # Special case for BrowserControlTool which uses a visuals subfolder
                    if isinstance(tool.output_dir, str) and "visuals" in tool.output_dir:
                        tool.output_dir = self.active_branch.visuals_path
                    else:
                        tool.output_dir = self.active_branch.project_path

        tool_schemas = [{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}} for t in self.tools.values()]
        messages = [
            {"role": "system", "content": f"You are {self.role}. {self.backstory}\nGoal: {self.goal}\nActive Project Branch: {self.active_branch.task_id}"},
            {"role": "user", "content": f"Context: {context}\n\nTask: {task_description}\n\nIMPORTANT: Use tools to find info. Provide a final written summary."}
        ]
        for _ in range(10):
            response = await litellm.acompletion(model=self.model_name, messages=messages, tools=tool_schemas if tool_schemas else None)
            resp_msg = response.choices[0].message
            messages.append(resp_msg)

            # Convert to dict for easier access if it's a message object
            if hasattr(resp_msg, "dict"):
                resp_dict = resp_msg.dict()
            else:
                resp_dict = resp_msg if isinstance(resp_msg, dict) else {}

            if resp_dict.get("tool_calls"):
                for tool_call in resp_dict["tool_calls"]:
                    if isinstance(tool_call, dict):
                        t_name = tool_call["function"]["name"]
                        t_args_str = tool_call["function"]["arguments"]
                        t_id = tool_call["id"]
                    else:
                        t_name = tool_call.function.name
                        t_args_str = tool_call.function.arguments
                        t_id = tool_call.id

                    try:
                        t_args = json.loads(t_args_str) if isinstance(t_args_str, str) else t_args_str
                    except json.JSONDecodeError:
                        print(f"  [Error] Failed to parse arguments for {t_name}: {t_args_str}")
                        continue

                    if t_name in self.tools:
                        print(f"  [{self.role}] calling {t_name}...")
                        try:
                            result = await self.tools[t_name].execute(**t_args)
                            if self.active_branch:
                                self.active_branch.log_tool_call(t_name, t_args, str(result))
                        except Exception as e:
                            print(f"  [Error] Tool {t_name} failed: {str(e)}")
                            result = f"Error: {str(e)}"
                        messages.append({"role": "tool", "name": t_name, "tool_call_id": t_id, "content": str(result)})
                continue 
            return {"output": resp_dict.get("content"), "prompt_tokens": response.usage.prompt_tokens, "completion_tokens": response.usage.completion_tokens}
        return {"output": "Max reasoning steps reached.", "error": "Loop timeout"}
