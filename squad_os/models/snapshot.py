from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TaskPlanSnapshot(BaseModel):
    description: str
    assigned_agent_role: str


class MissionSnapshot(BaseModel):
    """Full state snapshot for mission pause/resume.

    Captures the complete execution state at the moment an agent
    requests human input, enabling seamless context reconstruction
    on resume without agent amnesia.
    """
    mission_id: int
    goal: str
    execution_plan: List[TaskPlanSnapshot]
    current_step_index: int
    current_task_description: str
    agent_role: str

    reasoning_trace: List[Dict[str, Any]]
    short_term_memory: str

    interrupt_reason: str
    error_message: Optional[str] = None
    confidence_score: Optional[float] = None
    tool_calls_in_progress: List[Dict[str, Any]] = Field(default_factory=list)

    backtrack_counts: Dict[str, int] = Field(default_factory=dict)
    total_iteration_count: int

    quality_failure_count: int = 0

    prompt_tokens: int = 0
    completion_tokens: int = 0

    # Budget state — captured at interrupt for human top-up decisions
    max_tokens: int = 0
    max_turns: int = 0
    max_cost_usd: float = 0.0
    budget_exhausted: bool = False

    # Context state — summary of pruned conversation turns
    context_summary: str = ""

    captured_at: datetime = Field(default_factory=datetime.now)
