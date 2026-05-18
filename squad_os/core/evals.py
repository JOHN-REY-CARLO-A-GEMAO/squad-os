"""Automated Evaluation Harness for SquadOS.

Implements LLM-as-a-Judge evaluation of agent trajectories against
a golden dataset. Tracks Groundedness, Relevance, and Task Success
on a 5-point rubric to catch silent regressions.

Usage:
    python tests/run_evals.py                          # Run all evals
    python tests/run_evals.py --filter "tool_use"      # Run subset
    python tests/run_evals.py --compare results_v1.json  # Compare with prior run
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from litellm import acompletion

logger = logging.getLogger(__name__)


# --- EVAL SCHEMA ---

class EvalCriterion(BaseModel):
    """A single evaluation criterion with rubric."""
    name: str
    description: str
    weight: float = 1.0


class EvalCase(BaseModel):
    """A single test case in the golden dataset."""
    id: str
    name: str
    category: str  # e.g., "tool_use", "reasoning", "budget", "error_recovery"
    goal: str
    context: str = ""
    expected_tools: List[str] = Field(default_factory=list)
    expected_output_keywords: List[str] = Field(default_factory=list)
    anti_keywords: List[str] = Field(default_factory=list)  # Should NOT appear
    difficulty: str = "medium"  # easy, medium, hard
    notes: str = ""


class EvalResult(BaseModel):
    """Result of running a single eval case."""
    case_id: str
    case_name: str
    category: str
    difficulty: str

    # Agent output
    actual_output: str = ""
    tools_used: List[str] = Field(default_factory=list)
    error: Optional[str] = None

    # LLM-as-a-Judge scores (1-5)
    groundedness: int = 0
    groundedness_reason: str = ""
    relevance: int = 0
    relevance_reason: str = ""
    task_success: int = 0
    task_success_reason: str = ""

    # Computed
    weighted_score: float = 0.0
    duration_ms: float = 0.0
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    @property
    def raw_score(self) -> float:
        """Average of the three criterion scores."""
        scores = [s for s in [self.groundedness, self.relevance, self.task_success] if s > 0]
        return sum(scores) / len(scores) if scores else 0.0


class EvalRun(BaseModel):
    """Complete evaluation run results."""
    run_id: str
    model_name: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    avg_score: float = 0.0
    results: List[EvalResult] = Field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"Eval Run: {self.run_id}",
            f"Model: {self.model_name}",
            f"Timestamp: {self.timestamp}",
            f"Cases: {self.total_cases} ({self.passed_cases} passed, {self.failed_cases} failed)",
            f"Average Score: {self.avg_score:.2f} / 5.00",
            "",
            "By Category:",
        ]
        categories: Dict[str, List[EvalResult]] = {}
        for r in self.results:
            categories.setdefault(r.category, []).append(r)
        for cat, results in sorted(categories.items()):
            cat_avg = sum(r.raw_score for r in results) / len(results)
            lines.append(f"  {cat}: {cat_avg:.2f} ({len(results)} cases)")

        lines.append("")
        lines.append("By Difficulty:")
        difficulties: Dict[str, List[EvalResult]] = {}
        for r in self.results:
            difficulties.setdefault(r.difficulty, []).append(r)
        for diff, results in sorted(difficulties.items()):
            diff_avg = sum(r.raw_score for r in results) / len(results)
            lines.append(f"  {diff}: {diff_avg:.2f} ({len(results)} cases)")

        return "\n".join(lines)


# --- JUDGE PROMPTS ---

JUDGE_SYSTEM_PROMPT = """You are an expert evaluator of AI agent performance.
You will assess an agent's response to a task on three dimensions, each scored 1-5.

SCORING RUBRIC:

1. GROUNDEDNESS (1-5): How well does the output align with available tools and facts?
   1 = Completely hallucinated, ignores tools, makes up facts
   2 = Mostly fabricated, minimal tool alignment
   3 = Partially grounded, some tool use but gaps
   4 = Well-grounded, appropriate tool use, minor gaps
   5 = Fully grounded, excellent tool use, no hallucination

2. RELEVANCE (1-5): How directly does the output address the task?
   1 = Completely irrelevant, off-topic
   2 = Tangentially related, misses key requirements
   3 = Partially relevant, addresses some requirements
   4 = Mostly relevant, addresses most requirements
   5 = Highly relevant, fully addresses all requirements

3. TASK SUCCESS (1-5): Did the agent accomplish the goal?
   1 = Complete failure, no progress
   2 = Minimal progress, goal not achieved
   3 = Partial success, goal partially achieved
   4 = Near success, goal mostly achieved with minor issues
   5 = Full success, goal completely achieved

Return ONLY a JSON object with this structure:
{
  "groundedness": <1-5>,
  "groundedness_reason": "<brief explanation>",
  "relevance": <1-5>,
  "relevance_reason": "<brief explanation>",
  "task_success": <1-5>,
  "task_success_reason": "<brief explanation>"
}"""


async def llm_as_judge(
    goal: str,
    context: str,
    actual_output: str,
    tools_used: List[str],
    expected_tools: List[str],
    expected_keywords: List[str],
    anti_keywords: List[str],
    judge_model: str = "gpt-4o-mini",
) -> Dict[str, Any]:
    """Evaluate agent output using LLM-as-a-Judge pattern."""
    judge_prompt = f"""TASK: {goal}

CONTEXT PROVIDED: {context[:500] if context else "None"}

TOOLS AVAILABLE: {', '.join(expected_tools) if expected_tools else "None specified"}
TOOLS ACTUALLY USED: {', '.join(tools_used) if tools_used else "None"}

EXPECTED KEYWORDS/CONCEPTS: {', '.join(expected_keywords) if expected_keywords else "None specified"}
SHOULD NOT CONTAIN: {', '.join(anti_keywords) if anti_keywords else "None specified"}

AGENT OUTPUT:
{actual_output[:2000] if actual_output else "(empty output)"}

Evaluate the agent's performance and return ONLY a JSON object."""

    try:
        response = await acompletion(
            model=judge_model,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": judge_prompt},
            ],
            temperature=0.0,
        )
        content = response.choices[0].message.content or ""
        # Extract JSON from response
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
        return {}
    except Exception as e:
        logger.warning("LLM judge failed: %s", e)
        return {}


# --- EVAL RUNNER ---

class EvalRunner:
    """Runs evaluation cases and collects results."""

    def __init__(
        self,
        agent_executor,
        judge_model: str = "gpt-4o-mini",
        run_id: Optional[str] = None,
    ):
        self.agent_executor = agent_executor  # Callable: (goal, context) -> {output, tools_used}
        self.judge_model = judge_model
        self.run_id = run_id or f"eval-{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    async def run_case(self, case: EvalCase) -> EvalResult:
        """Run a single eval case and score it."""
        start = time.monotonic()
        result = EvalResult(
            case_id=case.id,
            case_name=case.name,
            category=case.category,
            difficulty=case.difficulty,
        )

        try:
            output = await self.agent_executor(case.goal, case.context)
            result.actual_output = output.get("output", "")
            result.tools_used = output.get("tools_used", [])
            result.error = output.get("error")
        except Exception as e:
            result.error = str(e)
            result.actual_output = f"Error: {e}"

        # LLM-as-a-Judge scoring
        if not result.error or "Error:" not in result.actual_output[:20]:
            scores = await llm_as_judge(
                goal=case.goal,
                context=case.context,
                actual_output=result.actual_output,
                tools_used=result.tools_used,
                expected_tools=case.expected_tools,
                expected_keywords=case.expected_keywords,
                anti_keywords=case.anti_keywords,
                judge_model=self.judge_model,
            )
            result.groundedness = scores.get("groundedness", 0)
            result.groundedness_reason = scores.get("groundedness_reason", "")
            result.relevance = scores.get("relevance", 0)
            result.relevance_reason = scores.get("relevance_reason", "")
            result.task_success = scores.get("task_success", 0)
            result.task_success_reason = scores.get("task_success_reason", "")

        result.duration_ms = (time.monotonic() - start) * 1000
        result.weighted_score = result.raw_score
        return result

    async def run_all(
        self,
        cases: List[EvalCase],
        filter_category: Optional[str] = None,
        filter_difficulty: Optional[str] = None,
    ) -> EvalRun:
        """Run all eval cases and return aggregated results."""
        filtered = cases
        if filter_category:
            filtered = [c for c in filtered if c.category == filter_category]
        if filter_difficulty:
            filtered = [c for c in filtered if c.difficulty == filter_difficulty]

        run = EvalRun(
            run_id=self.run_id,
            model_name=self.judge_model,
            total_cases=len(filtered),
        )

        for case in filtered:
            logger.info("Running eval: %s (%s)", case.name, case.id)
            result = await self.run_case(case)
            run.results.append(result)
            if result.raw_score >= 3.0:
                run.passed_cases += 1
            else:
                run.failed_cases += 1

        if run.results:
            run.avg_score = sum(r.raw_score for r in run.results) / len(run.results)

        return run


def load_golden_dataset(path: str) -> List[EvalCase]:
    """Load golden dataset from JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [EvalCase(**case) for case in data.get("cases", [])]


def save_results(run: EvalRun, path: str):
    """Save eval results to JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(run.model_dump(), f, indent=2, default=str)


def compare_runs(current: EvalRun, previous_path: str) -> str:
    """Compare current run with a previous run and return delta report."""
    if not os.path.exists(previous_path):
        return f"No previous results found at {previous_path}"

    with open(previous_path, "r", encoding="utf-8") as f:
        prev_data = json.load(f)
    prev_run = EvalRun(**prev_data)

    delta = current.avg_score - prev_run.avg_score
    delta_sign = "+" if delta >= 0 else ""

    lines = [
        f"=== EVAL COMPARISON ===",
        f"Previous: {prev_run.run_id} ({prev_run.timestamp}) — {prev_run.avg_score:.2f}",
        f"Current:  {current.run_id} ({current.timestamp}) — {current.avg_score:.2f}",
        f"Delta:    {delta_sign}{delta:.2f}",
        "",
    ]

    # Per-case comparison
    prev_results = {r.case_id: r for r in prev_run.results}
    changed = []
    for r in current.results:
        prev = prev_results.get(r.case_id)
        if prev:
            case_delta = r.raw_score - prev.raw_score
            if abs(case_delta) > 0.01:
                changed.append((r.case_id, r.case_name, prev.raw_score, r.raw_score, case_delta))

    if changed:
        lines.append("Changed Cases:")
        for case_id, name, prev_score, curr_score, delta in sorted(changed, key=lambda x: x[4]):
            sign = "+" if delta >= 0 else ""
            emoji = "↑" if delta > 0 else "↓"
            lines.append(f"  {emoji} {name}: {prev_score:.1f} → {curr_score:.1f} ({sign}{delta:.1f})")
    else:
        lines.append("No changes from previous run.")

    return "\n".join(lines)
