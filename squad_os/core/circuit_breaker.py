from typing import Optional


class QualityCircuitBreaker:
    """Quality-aware circuit breaker for LLM output validation.

    Tracks consecutive output failures per task. When the failure count
    exceeds the threshold, the circuit opens and the mission should
    pause for human review instead of retrying indefinitely.
    """

    def __init__(self, failure_threshold: int = 3):
        self.failure_threshold = failure_threshold
        self._failures: dict[int, int] = {}

    def record_failure(self, task_id: int) -> int:
        """Record a quality failure for the given task. Returns new count."""
        self._failures[task_id] = self._failures.get(task_id, 0) + 1
        return self._failures[task_id]

    def record_success(self, task_id: int):
        """Reset failure counter for a task on successful output."""
        self._failures.pop(task_id, None)

    def get_failure_count(self, task_id: int) -> int:
        return self._failures.get(task_id, 0)

    def is_open(self, task_id: int) -> bool:
        """Return True if the circuit is open (threshold exceeded)."""
        return self._failures.get(task_id, 0) >= self.failure_threshold

    def reset(self):
        self._failures.clear()


def validate_output_quality(output: str) -> tuple[bool, Optional[str]]:
    """Check if an LLM output passes basic quality gates.

    Returns (is_valid, reason_if_invalid).
    """
    if not output or not output.strip():
        return False, "Empty output"

    if len(output.strip()) < 5:
        return False, f"Output too short ({len(output.strip())} chars)"

    stripped = output.strip()
    if stripped.startswith("Error:") and len(stripped) < 50:
        return False, f"Short error output: {stripped[:100]}"

    if stripped.upper() in ("NONE", "NULL", "N/A", "UNKNOWN", "ERROR"):
        return False, f"Placeholder output: {stripped}"

    return True, None
