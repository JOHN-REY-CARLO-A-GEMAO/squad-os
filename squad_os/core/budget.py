from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TokenBudget:
    max_total_tokens: int = 0
    max_prompt_tokens: int = 0
    max_completion_tokens: int = 0
    max_cost_usd: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost_usd: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def exceeded(self) -> bool:
        if self.max_total_tokens and self.total_tokens >= self.max_total_tokens:
            return True
        if self.max_prompt_tokens and self.prompt_tokens >= self.max_prompt_tokens:
            return True
        if self.max_completion_tokens and self.completion_tokens >= self.max_completion_tokens:
            return True
        if self.max_cost_usd and self.total_cost_usd >= self.max_cost_usd:
            return True
        return False

    def add_usage(self, prompt_tokens: int, completion_tokens: int, cost_usd: float = 0.0) -> bool:
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.total_cost_usd += cost_usd
        return not self.exceeded

    def snapshot(self) -> dict:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "budget_exceeded": self.exceeded,
        }
