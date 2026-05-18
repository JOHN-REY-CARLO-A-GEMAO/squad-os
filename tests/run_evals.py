#!/usr/bin/env python
"""CLI utility to run SquadOS evaluations against the golden dataset.

Usage:
    python tests/run_evals.py                          # Run all evals
    python tests/run_evals.py --filter tool_use        # Run specific category
    python tests/run_evals.py --difficulty hard        # Run specific difficulty
    python tests/run_evals.py --compare results.json   # Compare with prior run
    python tests/run_evals.py --output results_v2.json # Save results
"""

import argparse
import asyncio
import json
import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from squad_os.core.evals import (
    EvalRunner,
    EvalCase,
    EvalResult,
    load_golden_dataset,
    save_results,
    compare_runs,
)
from squad_os.core.logging import setup_root_logger, get_logger


class MockAgentExecutor:
    """Mock agent executor for testing the eval harness without a live LLM.

    Replace this with a real agent executor for production evals:
        async def execute(goal, context):
            # Run actual agent
            return {"output": result, "tools_used": tools}
    """

    def __init__(self):
        self.call_count = 0

    async def __call__(self, goal: str, context: str) -> dict:
        self.call_count += 1
        # Simulate agent behavior for testing
        await asyncio.sleep(0.1)  # Simulate latency

        # Basic mock responses based on goal keywords
        if "hello" in goal.lower() or "hi" in goal.lower():
            return {"output": "Hello! How can I help you today?", "tools_used": []}

        if "fibonacci" in goal.lower():
            return {
                "output": "I've written the fibonacci function to fib.py. The function calculates fibonacci numbers recursively.",
                "tools_used": ["write_file", "read_file"],
            }

        if "search" in goal.lower() or "trends" in goal.lower():
            return {
                "output": "Based on my search, the top Python web frameworks in 2026 are FastAPI, Django, and Starlette.",
                "tools_used": ["web_search"],
            }

        if "prime" in goal.lower():
            return {
                "output": "The first 10 prime numbers are: 2, 3, 5, 7, 11, 13, 17, 19, 23, 29.",
                "tools_used": ["python_runner"],
            }

        if "blackboard" in goal.lower() or "shared" in goal.lower():
            return {
                "output": "I've stored project_status: in_progress on the blackboard and confirmed it.",
                "tools_used": ["set_shared_value", "get_shared_value"],
            }

        if "nonexistent" in goal.lower():
            return {
                "output": "The file didn't exist, so I created it with placeholder content and read it back successfully.",
                "tools_used": ["read_file", "write_file"],
            }

        if "quantum" in goal.lower():
            return {
                "output": "DELEGATED: I've delegated the quantum computing research to a specialist who found applications in post-quantum cryptography.",
                "tools_used": ["delegate_task"],
            }

        if "passwd" in goal.lower() or "etc/" in goal.lower():
            return {
                "output": "Error: Access denied. Path is outside the workspace.",
                "tools_used": ["read_file"],
            }

        if "readme" in goal.lower() or "commit" in goal.lower():
            return {
                "output": "I've created README.md with project documentation and committed all artifacts successfully.",
                "tools_used": ["write_file", "commit_project"],
            }

        if "ambiguous" in goal.lower() or "analyze the data" in goal.lower():
            return {
                "output": "I'd need you to specify what data you'd like me to analyze. Could you provide the dataset or clarify the scope?",
                "tools_used": [],
            }

        if "budget" in goal.lower() or "computing" in goal.lower():
            return {
                "output": "The history of computing spans from mechanical calculators to modern quantum systems. Key milestones: Turing machine (1936), ENIAC (1945), microprocessors (1971), internet (1990s), AI era (2020s).",
                "tools_used": [],
            }

        if "divide by zero" in goal.lower():
            return {
                "output": "The script had a division by zero error. I've fixed it by adding a check for zero denominator.",
                "tools_used": ["python_runner"],
            }

        if "list" in goal.lower() and "files" in goal.lower():
            return {
                "output": "Found 15 files in the workspace directory.",
                "tools_used": ["terminal"],
            }

        if "memory" in goal.lower():
            return {
                "output": "Found 2 past tasks related to API: one about REST API design and another about GraphQL implementation.",
                "tools_used": ["memory_search"],
            }

        # Default fallback
        return {
            "output": f"I've processed the task: {goal[:50]}...",
            "tools_used": [],
        }


async def run_evals(args):
    """Main eval runner."""
    setup_root_logger()
    log = get_logger("squad_os.evals")

    # Load golden dataset
    dataset_path = os.path.join(os.path.dirname(__file__), "golden_dataset.json")
    if not os.path.exists(dataset_path):
        print(f"Error: Golden dataset not found at {dataset_path}")
        sys.exit(1)

    cases = load_golden_dataset(dataset_path)
    log.info("Loaded golden dataset", total_cases=len(cases))

    # Filter cases
    if args.filter:
        cases = [c for c in cases if c.category == args.filter]
        log.info("Filtered by category", category=args.filter, remaining=len(cases))

    if args.difficulty:
        cases = [c for c in cases if c.difficulty == args.difficulty]
        log.info("Filtered by difficulty", difficulty=args.difficulty, remaining=len(cases))

    if not cases:
        print("No eval cases match the filters.")
        sys.exit(0)

    # Create runner
    executor = MockAgentExecutor()
    runner = EvalRunner(
        agent_executor=executor,
        judge_model=args.judge_model,
    )

    print(f"Running {len(cases)} eval cases...")
    print(f"Judge model: {args.judge_model}")
    print()

    start = time.monotonic()
    run = await runner.run_all(cases)
    elapsed = (time.monotonic() - start) * 1000

    # Print results
    print(run.summary())
    print(f"\nTotal time: {elapsed/1000:.1f}s")
    print(f"Agent calls: {executor.call_count}")

    # Save results
    if args.output:
        save_results(run, args.output)
        print(f"\nResults saved to {args.output}")

    # Compare with previous run
    if args.compare:
        print()
        print(compare_runs(run, args.compare))

    # Print detailed failures
    failures = [r for r in run.results if r.raw_score < 3.0]
    if failures:
        print("\n--- FAILURES (score < 3.0) ---")
        for r in failures:
            print(f"\n  Case: {r.case_name} ({r.case_id})")
            print(f"  Score: {r.raw_score:.1f}/5.0")
            print(f"  Groundedness: {r.groundedness}/5 - {r.groundedness_reason}")
            print(f"  Relevance: {r.relevance}/5 - {r.relevance_reason}")
            print(f"  Task Success: {r.task_success}/5 - {r.task_success_reason}")
            if r.error:
                print(f"  Error: {r.error}")

    # Exit code based on pass rate
    pass_rate = run.passed_cases / run.total_cases if run.total_cases > 0 else 0
    if pass_rate < 0.8:
        print(f"\n⚠️  Pass rate below 80% ({pass_rate:.0%}). Review failures above.")
        sys.exit(1)
    else:
        print(f"\n✅ Pass rate: {pass_rate:.0%}")
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="Run SquadOS golden dataset evaluations")
    parser.add_argument(
        "--filter",
        type=str,
        help="Filter by category (e.g., tool_use, reasoning, budget, error_recovery)",
    )
    parser.add_argument(
        "--difficulty",
        type=str,
        choices=["easy", "medium", "hard"],
        help="Filter by difficulty level",
    )
    parser.add_argument(
        "--judge-model",
        type=str,
        default="gpt-4o-mini",
        help="Model to use for LLM-as-a-Judge (default: gpt-4o-mini)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save results to JSON file",
    )
    parser.add_argument(
        "--compare",
        type=str,
        help="Compare with previous results file",
    )
    args = parser.parse_args()
    asyncio.run(run_evals(args))


if __name__ == "__main__":
    main()
