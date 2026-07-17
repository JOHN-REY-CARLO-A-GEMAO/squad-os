import json
import time
from typing import Dict, List, Optional, Any
from squad_os.core.gates import Gate

from squad_os.core.gates import GateSuite, VerificationReport, Gate

READ_ONLY_TOOLS_PROMPT = (
    "You are a Verifier Agent. Your only job is to CHECK work — you must NEVER write or modify code. "
    "You have read-only access to the workspace. Review the task output and determine if it meets the requirements. "
    "Respond with a structured verdict."
)


class VerifierAgent:
    """Independent checker that never writes code, only verifies through gates and read-only review.

    Follows the maker/checker split pattern from loop engineering:
    - Maker: creates code/tools/output
    - Verifier: checks gates, reads output, produces verdict
    - The verifier NEVER has write-capable tools
    """

    def __init__(self, gates: Optional[List[Gate]] = None):
        self.gate_suite = GateSuite(gates=gates or [])

    async def verify(
        self,
        workspace: str,
        task_description: str,
        agent_output: str,
        task_idx: int = 0,
        gate_names: Optional[List[str]] = None,
    ) -> VerificationReport:
        """Run all deterministic gates against the task output.

        This is the primary verification path — external, objective, non-LLM checks.
        If gate_names is provided, only those named gates are executed.
        """
        report = await self.gate_suite.run_all(workspace, task_description, agent_output, gate_names=gate_names)
        report.task_idx = task_idx
        return report

    async def verify_with_review(
        self,
        workspace: str,
        task_description: str,
        agent_output: str,
        task_idx: int = 0,
        llm_client=None,
    ) -> VerificationReport:
        """Run gates first, then optionally do an LLM-based review.

        The LLM review is a SECONDARY check — the deterministic gates are the primary oracle.
        The LLM reviewer has NO write tools and only reads the existing output.
        """
        report = await self.verify(workspace, task_description, agent_output, task_idx)

        if llm_client and report.all_required_passed:
            review = await self._llm_review(llm_client, task_description, agent_output)
            if review:
                report.results.append(review)

        return report

    async def _llm_review(self, llm_client, task_description: str, agent_output: str) -> Any:
        """Lightweight LLM-based review pass (non-deterministic, advisory)."""
        try:
            import litellm
            response = await litellm.acompletion(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": READ_ONLY_TOOLS_PROMPT},
                    {"role": "user", "content": (
                        f"Task: {task_description}\n\n"
                        f"Agent Output:\n{agent_output[:4000]}\n\n"
                        f"Review the output. Does it satisfy the task requirements?\n"
                        f"Verdict (PASS/FAIL):\n"
                        f"Reasoning (2-3 sentences):"
                    )}
                ]
            )
            content = response.choices[0].message.content or ""
            passed = "PASS" in content.upper() and "FAIL" not in content.upper().split("PASS")[-1][:10]
            from squad_os.core.gates import GateResult
            return GateResult(
                status="PASS" if passed else "FAIL",
                gate_name="llm_review",
                details=content[:500],
                duration_ms=0.0,
            )
        except Exception:
            return None
