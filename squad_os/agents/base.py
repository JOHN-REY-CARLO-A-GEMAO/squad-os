import os
import json
import asyncio
from typing import Any, Dict, List, Optional
import litellm
from squad_os.tools.base import BaseTool, RetryExhaustedResult
from squad_os.core.projects import ProjectBranch
from squad_os.core.exceptions import ToolRiskException
from squad_os.core.tool_risk import RISK_LABELS
from squad_os.core.context import ContextManager

# Global semaphore for LLM calls to prevent rate-limit exhaustion
# Configurable via env var for different Ollama/hardware setups
try:
    _LLM_CONCURRENCY_LIMIT = int(os.environ.get("SQUAD_OS_LLM_CONCURRENCY", 5))
    if _LLM_CONCURRENCY_LIMIT <= 0:
        _LLM_CONCURRENCY_LIMIT = 5
except ValueError:
    _LLM_CONCURRENCY_LIMIT = 5
_LLM_SEMAPHORE = asyncio.Semaphore(_LLM_CONCURRENCY_LIMIT)

# Default context window settings
_DEFAULT_MAX_HISTORY_TURNS = int(os.environ.get("SQUAD_OS_CTX_MAX_TURNS", 5))
_DEFAULT_MAX_MESSAGES = int(os.environ.get("SQUAD_OS_CTX_MAX_MSG", 20))


class BaseAgent:
    def __init__(
        self,
        role: str,
        goal: str,
        backstory: str,
        tools: List[BaseTool] = None,
        model_name: str = "gpt-4o-mini",
        branch_id: str = None,
        max_history_turns: int = _DEFAULT_MAX_HISTORY_TURNS,
        max_messages: int = _DEFAULT_MAX_MESSAGES,
    ):
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.model_name = model_name
        self.tools = {t.name: t for t in (tools or [])}
        self.active_branch: Optional[ProjectBranch] = None
        if branch_id:
            self.active_branch = ProjectBranch(branch_id)
        self.max_history_turns = max_history_turns
        self.max_messages = max_messages

    async def execute_task(
        self,
        task_description: str,
        context: str,
        context_manager: Optional[ContextManager] = None,
    ) -> Dict[str, Any]:
        if not self.active_branch:
            branch_id = ProjectBranch.create_id(task_description[:30])
            self.active_branch = ProjectBranch(branch_id)
            self.active_branch.fork()
            print(f" [Fork]: Created new branch {branch_id}")

        # Inject active branch into all tools
        for tool in self.tools.values():
            if hasattr(tool, "workspace"):
                tool.workspace = self.active_branch.project_path
            if hasattr(tool, "output_dir"):
                if isinstance(tool.output_dir, str) and "visuals" in tool.output_dir:
                    tool.output_dir = self.active_branch.visuals_path
                else:
                    tool.output_dir = self.active_branch.project_path
            if hasattr(tool, "active_branch"):
                tool.active_branch = self.active_branch

        tool_schemas = [
            {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}}
            for t in self.tools.values()
        ]

        system_content = (
            f"You are {self.role}. {self.backstory}\n"
            f"Goal: {self.goal}\n"
            f"Active Project Branch: {self.active_branch.task_id}"
        )

        # Use provided context manager (resume) or create new one
        if context_manager is not None:
            ctx = context_manager
        else:
            ctx = ContextManager(
                max_history_turns=self.max_history_turns,
                max_messages=self.max_messages,
            )

        # Build initial messages
        ctx.add_message({"role": "system", "content": system_content})
        user_content = (
            f"Context: {context}\n\n"
            f"Task: {task_description}\n\n"
            f"IMPORTANT: Use tools to complete the task. "
            f"Once the tool call succeeds, stop calling tools and provide a short final text summary of what was done."
        )
        if ctx.summary:
            user_content = ctx.get_context_with_summary(user_content)
        ctx.add_message({"role": "user", "content": user_content})

        for _ in range(10):
            # Prune context before each LLM call to prevent window overflow
            ctx.prune()
            messages = ctx.get_messages()

            # Use semaphore to prevent API rate-limit exhaustion
            async with _LLM_SEMAPHORE:
                response = await litellm.acompletion(
                    model=self.model_name,
                    messages=messages,
                    tools=tool_schemas if tool_schemas else None
                )
            resp_msg = response.choices[0].message
            ctx.add_message(resp_msg)

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
                        tool = self.tools[t_name]
                        risk_tier = getattr(tool, "risk_tier", 3)
                        if risk_tier >= 3:
                            raise ToolRiskException(
                                tool_name=t_name,
                                tool_args=t_args,
                                risk_tier=risk_tier,
                                risk_label=RISK_LABELS.get(risk_tier, "Unknown"),
                                messages=ctx.get_messages(),
                            )
                        print(f"  [{self.role}] calling {t_name}...")
                        try:
                            result = await tool.execute(**t_args)
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

                        ctx.add_message({
                            "role": "tool",
                            "name": t_name,
                            "tool_call_id": t_id,
                            "content": str(result)
                        })
                    else:
                        # Tool not found — append a clear error so model stops retrying
                        ctx.add_message({
                            "role": "tool",
                            "name": t_name,
                            "tool_call_id": t_id,
                            "content": f"Error: Tool '{t_name}' is not available."
                        })
                        all_succeeded = False

                # If all tools succeeded, add a nudge to stop and summarize
                if all_succeeded:
                    ctx.add_message({
                        "role": "user",
                        "content": "All tools executed successfully. Now provide a short text summary of what was accomplished. Do not call any more tools."
                    })
                continue

            # No tool calls — model gave a text response, we're done
            return {
                "output": resp_dict.get("content"),
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "context_summary": ctx.summary,
            }

        return {"output": "Max reasoning steps reached.", "error": "Loop timeout", "context_summary": ctx.summary}