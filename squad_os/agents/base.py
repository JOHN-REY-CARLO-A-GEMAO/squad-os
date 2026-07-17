import os
import json
import asyncio
from typing import Any, Dict, List, Optional
import litellm
from squad_os.tools.base import BaseTool, RetryExhaustedResult
from squad_os.core.projects import ProjectBranch
from squad_os.core.budget import TokenBudget

# Global semaphore for LLM calls to prevent rate-limit exhaustion
# Configurable via env var for different Ollama/hardware setups
try:
    _LLM_CONCURRENCY_LIMIT = int(os.environ.get("SQUAD_OS_LLM_CONCURRENCY", 5))
    if _LLM_CONCURRENCY_LIMIT <= 0:
        _LLM_CONCURRENCY_LIMIT = 5
except ValueError:
    _LLM_CONCURRENCY_LIMIT = 5
_LLM_SEMAPHORE = asyncio.Semaphore(_LLM_CONCURRENCY_LIMIT)


class BaseAgent:
    def __init__(self, role: str, goal: str, backstory: str, tools: List[BaseTool] = None, model_name: str = "gpt-4o-mini", branch_id: str = None, token_budget: Optional[TokenBudget] = None):
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.model_name = model_name
        self.tools = {t.name: t for t in (tools or [])}
        self.active_branch: Optional[ProjectBranch] = None
        self.task_workspace: Optional[str] = None
        self.token_budget = token_budget or TokenBudget()
        if branch_id:
            self.active_branch = ProjectBranch(branch_id)

    async def execute_task(self, task_description: str, context: str) -> Dict[str, Any]:
        if not self.active_branch:
            branch_id = ProjectBranch.create_id(task_description[:30])
            self.active_branch = ProjectBranch(branch_id)
            self.active_branch.fork()
            print(f" [Fork]: Created new branch {branch_id}")

        # Inject active branch and per-task workspace into all tools
        tool_workspace = self.task_workspace if self.task_workspace else self.active_branch.project_path
        for tool in self.tools.values():
            if hasattr(tool, "workspace"):
                tool.workspace = tool_workspace
            if hasattr(tool, "output_dir"):
                if isinstance(tool.output_dir, str) and "visuals" in tool.output_dir:
                    if self.task_workspace:
                        tool.output_dir = os.path.join(self.task_workspace, "visuals")
                    else:
                        tool.output_dir = self.active_branch.visuals_path
                else:
                    tool.output_dir = tool_workspace
            if hasattr(tool, "active_branch"):
                tool.active_branch = self.active_branch

        # Save original tools so permanent mutation never leaks across task calls
        original_tools = dict(self.tools)

        # Check if task description mandates a specific tool
        import re
        must_use_match = re.search(r"MUST use (\w+) tool", task_description)
        if must_use_match:
            required_tool_name = must_use_match.group(1)
            if required_tool_name in self.tools:
                restricted = {required_tool_name: self.tools[required_tool_name]}
                self.tools = restricted
                print(f"  [{self.role}] Task requires '{required_tool_name}' — restricted toolset to required tool.")
                task_description += (
                    f"\n\nCRITICAL: You MUST call the '{required_tool_name}' tool function. "
                    "Do NOT respond with text only — you must execute the tool call."
                )
            else:
                # Required tool not available — inject it dynamically from global registry
                try:
                    from squad_os.tools.marketplace import SkillRegistry
                    reg = SkillRegistry.get_instance()
                    tool_instance = reg.get_tool(required_tool_name)
                    if tool_instance:
                        self.tools[required_tool_name] = tool_instance
                        if hasattr(tool_instance, "workspace") and self.active_branch:
                            tool_instance.workspace = self.task_workspace if self.task_workspace else self.active_branch.project_path
                        if hasattr(tool_instance, "active_branch"):
                            tool_instance.active_branch = self.active_branch
                        restricted = {required_tool_name: self.tools[required_tool_name]}
                        self.tools = restricted
                        print(f"  [{self.role}] Task requires '{required_tool_name}' — dynamically injected from registry, restricted toolset.")
                        task_description += (
                            f"\n\nCRITICAL: You MUST call the '{required_tool_name}' tool function. "
                            "Do NOT respond with text only — you must execute the tool call."
                        )
                except Exception:
                    print(f"  [{self.role}] WARNING: Task requires '{required_tool_name}' but it's not available in tools or registry.")

        tool_schemas = [
            {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}}
            for t in self.tools.values()
        ]

        messages = [
            {
                "role": "system",
                "content": (
                    f"You are {self.role}. {self.backstory}\n"
                    f"Goal: {self.goal}\n"
                    f"Active Project Branch: {self.active_branch.task_id}"
                )
            },
            {
                "role": "user",
                "content": (
                    f"Context: {context}\n\n"
                    f"Task: {task_description}\n\n"
                    f"IMPORTANT: Use tools to complete the task. "
                    f"Once the tool call succeeds, stop calling tools and provide a short final text summary of what was done."
                )
            }
        ]

        try:
            for _ in range(10):
                # Use semaphore to prevent API rate-limit exhaustion
                async with _LLM_SEMAPHORE:
                    response = await litellm.acompletion(
                        model=self.model_name,
                        messages=messages,
                        tools=tool_schemas if tool_schemas else None
                    )

                # Track token usage and enforce budget
                usage = response.usage
                pt = getattr(usage, "prompt_tokens", 0) or 0
                ct = getattr(usage, "completion_tokens", 0) or 0
                cost = getattr(usage, "cost", 0.0) or 0.0
                if not self.token_budget.add_usage(pt, ct, cost):
                    print(f"  [{self.role}] TOKEN BUDGET EXCEEDED: "
                          f"{self.token_budget.total_tokens} tokens, "
                          f"${self.token_budget.total_cost_usd:.4f}")
                    return {
                        "output": f"Token budget exceeded after "
                                  f"{self.token_budget.total_tokens} total tokens.",
                        "error": "BUDGET_EXCEEDED",
                        "token_budget": self.token_budget.snapshot(),
                    }

                resp_msg = response.choices[0].message
                messages.append(resp_msg)

                # Convert to dict for easier access - use model_dump() for Pydantic v2 compatibility
                # with fallback to dict() or direct dict conversion
                if isinstance(resp_msg, dict):
                    resp_dict = resp_msg
                elif hasattr(resp_msg, "model_dump"):
                    resp_dict = resp_msg.model_dump()
                elif hasattr(resp_msg, "dict"):
                    resp_dict = resp_msg.dict()
                else:
                    resp_dict = {}

                tool_calls = resp_dict.get("tool_calls")

                # Fallback: Some models (glm-4.7) return tool calls as JSON in content
                if not tool_calls:
                    content = resp_dict.get("content", "")
                    # Try to extract JSON tool call from content
                    if "```json" in content:
                        import re
                        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
                        if json_match:
                            try:
                                tc_data = json.loads(json_match.group(1))
                                if "name" in tc_data and "arguments" in tc_data:
                                    tool_calls = [{
                                        "function": {"name": tc_data["name"], "arguments": json.dumps(tc_data["arguments"])},
                                        "id": "fallback_id"
                                    }]
                            except json.JSONDecodeError:
                                pass
                    elif content.strip().startswith("{") and content.strip().endswith("}"):
                        try:
                            tc_data = json.loads(content.strip())
                            if "name" in tc_data and "arguments" in tc_data:
                                tool_calls = [{
                                    "function": {"name": tc_data["name"], "arguments": json.dumps(tc_data["arguments"])},
                                    "id": "fallback_id"
                                }]
                        except json.JSONDecodeError:
                            pass

                if tool_calls:
                    all_succeeded = True
                    for tool_call in tool_calls:
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
                            all_succeeded = False
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
                                all_succeeded = False

                            fallback_name = None
                            error_msg = None

                            if isinstance(result, RetryExhaustedResult):
                                fallback_name = result.fallback_name
                                error_msg = result.error
                            elif str(result).startswith("RETRY_EXHAUSTED:"):
                                parts = str(result).split("|")
                                error_msg = parts[0].replace("RETRY_EXHAUSTED:", "")
                                for part in parts[1:]:
                                    if part.startswith("FALLBACK:"):
                                        fallback_name = part.replace("FALLBACK:", "").strip()
                                        break

                            if fallback_name:
                                if fallback_name in self.tools:
                                    print(f"  [{self.role}] primary tool failed ({error_msg}), trying fallback: {fallback_name}...")
                                    try:
                                        fb_result = await self.tools[fallback_name].execute(**t_args)
                                        if self.active_branch:
                                            self.active_branch.log_tool_call(fallback_name, t_args, str(fb_result))
                                        result = fb_result
                                    except Exception as fb_e:
                                        result = f"Primary failed ({error_msg}) and fallback also failed: {fb_e}"
                                        all_succeeded = False
                                else:
                                    result = f"Primary tool exhausted ({error_msg}), fallback '{fallback_name}' not available."
                                    all_succeeded = False

                            messages.append({
                                "role": "tool",
                                "name": t_name,
                                "tool_call_id": t_id,
                                "content": str(result)
                            })
                        else:
                            # Tool not found — append a clear error so model stops retrying
                            messages.append({
                                "role": "tool",
                                "name": t_name,
                                "tool_call_id": t_id,
                                "content": f"Error: Tool '{t_name}' is not available."
                            })
                            all_succeeded = False

                    # If all tools succeeded, add a nudge to stop and summarize
                    if all_succeeded:
                        messages.append({
                            "role": "user",
                            "content": "All tools executed successfully. Now provide a short text summary of what was accomplished. Do not call any more tools."
                        })
                    continue

                # No tool calls — model gave a text response, we're done
                return {
                    "output": resp_dict.get("content"),
                    "prompt_tokens": self.token_budget.prompt_tokens,
                    "completion_tokens": self.token_budget.completion_tokens,
                    "token_budget": self.token_budget.snapshot(),
                }
        finally:
            self.tools = original_tools

        return {
            "output": "Max reasoning steps reached.",
            "error": "Loop timeout",
            "token_budget": self.token_budget.snapshot(),
        }