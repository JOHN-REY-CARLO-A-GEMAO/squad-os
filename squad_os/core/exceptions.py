from typing import Any, Dict, List, Optional


class AgentInterruptException(Exception):
    """Raised when an agent explicitly requests human input during execution."""

    def __init__(
        self,
        reason: str,
        messages: Optional[List[Dict[str, Any]]] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ):
        self.reason = reason
        self.messages = messages or []
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        super().__init__(reason)


class ToolRiskException(Exception):
    """Raised when a high-risk tool (T3/T4) requires human approval before execution."""

    def __init__(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        risk_tier: int,
        risk_label: str,
        messages: Optional[List[Dict[str, Any]]] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ):
        self.tool_name = tool_name
        self.tool_args = tool_args
        self.risk_tier = risk_tier
        self.risk_label = risk_label
        self.messages = messages or []
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        super().__init__(f"Tool '{tool_name}' (Tier {risk_tier}: {risk_label}) requires human approval")
