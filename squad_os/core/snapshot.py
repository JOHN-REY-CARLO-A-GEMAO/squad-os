from typing import Any, Dict, List, Optional

from squad_os.models.snapshot import MissionSnapshot, TaskPlanSnapshot
from squad_os.database.session import (
    create_interrupt,
    get_pending_interrupt_by_id,
)


async def capture_snapshot(
    mission_id: int,
    goal: str,
    plan_tasks: List[Any],
    task_idx: int,
    current_task_desc: str,
    agent_role: str,
    messages: List[Dict[str, Any]],
    context: str,
    backtrack_counts: Dict[str, int],
    total_iterations: int,
    reason: str,
    error_message: Optional[str] = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    quality_failure_count: int = 0,
    max_tokens: int = 0,
    max_turns: int = 0,
    max_cost_usd: float = 0.0,
    budget_exhausted: bool = False,
    context_summary: str = "",
) -> int:
    """Serialize full mission state and create a PENDING interrupt.

    This is the 'freeze' hook — called when an agent requests human input.
    Captures the complete execution context so the agent can resume
    without losing its reasoning chain.
    """
    snapshot = MissionSnapshot(
        mission_id=mission_id,
        goal=goal,
        execution_plan=[
            TaskPlanSnapshot(description=t.description, assigned_agent_role=t.assigned_agent_role)
            for t in plan_tasks
        ],
        current_step_index=task_idx,
        current_task_description=current_task_desc,
        agent_role=agent_role,
        reasoning_trace=messages,
        short_term_memory=context,
        interrupt_reason=reason,
        error_message=error_message,
        backtrack_counts=backtrack_counts,
        total_iteration_count=total_iterations,
        quality_failure_count=quality_failure_count,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        max_tokens=max_tokens,
        max_turns=max_turns,
        max_cost_usd=max_cost_usd,
        budget_exhausted=budget_exhausted,
        context_summary=context_summary,
    )
    return await create_interrupt(
        mission_id=mission_id,
        task_idx=task_idx,
        context=snapshot.model_dump_json(),
        error_message=reason,
    )


async def restore_snapshot(interrupt_id: int) -> MissionSnapshot:
    """Fetch a pending interrupt and deserialize its snapshot.

    Returns the MissionSnapshot so the manager can reconstruct
    task_idx, context, plan, and retry state.
    """
    interrupt = await get_pending_interrupt_by_id(interrupt_id)
    if not interrupt or not interrupt.get("context"):
        raise ValueError(f"No snapshot found for interrupt {interrupt_id}")

    return MissionSnapshot.model_validate_json(interrupt["context"])
