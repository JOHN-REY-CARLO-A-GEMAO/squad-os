from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal, List, Optional
import asyncio
import os
import subprocess
import time


GateStatus = Literal["PASS", "FAIL", "ERROR"]


@dataclass
class GateResult:
    status: GateStatus
    gate_name: str
    details: str = ""
    duration_ms: float = 0.0
    required: bool = True

    @property
    def passed(self) -> bool:
        return self.status == "PASS"


class Gate(ABC):
    name: str = ""
    description: str = ""
    required: bool = True

    @abstractmethod
    async def verify(self, workspace: str, task_description: str, agent_output: str) -> GateResult:
        ...


class TestGate(Gate):
    name = "test_suite"
    description = "Discovers and runs pytest tests in the workspace. Passes if all tests pass."

    async def verify(self, workspace: str, task_description: str, agent_output: str) -> GateResult:
        start = time.time()
        test_dirs = self._discover_test_dirs(workspace)
        if not test_dirs:
            return GateResult(
                status="PASS", gate_name=self.name,
                details="No test files found — gate skipped.",
                duration_ms=(time.time() - start) * 1000
            )

        results = []
        for test_dir in test_dirs:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "python", "-m", "pytest", test_dir, "-x", "--no-header", "-q",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=workspace
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
                if proc.returncode == 0:
                    results.append(f"[PASS] {test_dir}")
                else:
                    output = (stdout.decode() + stderr.decode()).strip()
                    results.append(f"[FAIL] {test_dir}\n{output[:500]}")
            except asyncio.TimeoutError:
                results.append(f"[ERROR] {test_dir} — timed out after 120s")
            except FileNotFoundError:
                return GateResult(
                    status="ERROR", gate_name=self.name,
                    details="pytest not found in environment.",
                    duration_ms=(time.time() - start) * 1000
                )

        elapsed_ms = (time.time() - start) * 1000
        all_pass = all(r.startswith("[PASS]") for r in results)
        return GateResult(
            status="PASS" if all_pass else "FAIL",
            gate_name=self.name,
            details="\n".join(results),
            duration_ms=elapsed_ms
        )

    @staticmethod
    def _discover_test_dirs(workspace: str) -> List[str]:
        candidates = []
        for entry in os.listdir(workspace):
            full = os.path.join(workspace, entry)
            if os.path.isdir(full) and entry in ("tests", "test"):
                candidates.append(full)
            elif os.path.isfile(full) and entry.startswith("test_") and entry.endswith(".py"):
                candidates.append(full)
        return candidates


class LintGate(Gate):
    name = "lint"
    description = "Runs ruff linter on the workspace. Passes if no lint errors."
    required = False

    async def verify(self, workspace: str, task_description: str, agent_output: str) -> GateResult:
        start = time.time()
        try:
            proc = await asyncio.create_subprocess_exec(
                "python", "-m", "ruff", "check", workspace,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
            elapsed_ms = (time.time() - start) * 1000
            output = (stdout.decode() + stderr.decode()).strip()
            if proc.returncode == 0:
                return GateResult(status="PASS", gate_name=self.name, details="No lint errors.", duration_ms=elapsed_ms)
            if "No module named" in output:
                return GateResult(status="PASS", gate_name=self.name,
                    details="ruff not installed — gate skipped.", duration_ms=elapsed_ms)
            return GateResult(
                status="FAIL", gate_name=self.name,
                details=output[:1000],
                duration_ms=elapsed_ms
            )
        except FileNotFoundError:
                return GateResult(
                    status="PASS", gate_name=self.name,
                    details="ruff not available — gate skipped.",
                    duration_ms=(time.time() - start) * 1000
                )


class TypeCheckGate(Gate):
    name = "type_check"
    description = "Runs mypy type checker on the workspace. Passes if no type errors."
    required = False

    async def verify(self, workspace: str, task_description: str, agent_output: str) -> GateResult:
        start = time.time()
        try:
            proc = await asyncio.create_subprocess_exec(
                "python", "-m", "mypy", workspace, "--ignore-missing-imports",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            elapsed_ms = (time.time() - start) * 1000
            output = (stdout.decode() + stderr.decode()).strip()
            if proc.returncode == 0:
                return GateResult(status="PASS", gate_name=self.name, details="No type errors.", duration_ms=elapsed_ms)
            if "No module named" in output:
                return GateResult(status="PASS", gate_name=self.name,
                    details="mypy not installed — gate skipped.", duration_ms=elapsed_ms)
            return GateResult(
                status="FAIL", gate_name=self.name,
                details=output[:1000],
                duration_ms=elapsed_ms
            )
        except FileNotFoundError:
            return GateResult(
                status="PASS", gate_name=self.name,
                details="mypy not available — gate skipped.",
                duration_ms=(time.time() - start) * 1000
            )


class FileExistsGate(Gate):
    name = "file_exists"
    description = "Checks that specific files exist in the workspace."

    def __init__(self, required_files: List[str]):
        self._required_files = required_files
        super().__init__()

    async def verify(self, workspace: str, task_description: str, agent_output: str) -> GateResult:
        start = time.time()
        missing = []
        found = []
        for f in self._required_files:
            full = os.path.join(workspace, f)
            if os.path.exists(full):
                found.append(f)
            else:
                missing.append(f)
        elapsed_ms = (time.time() - start) * 1000
        if not missing:
            return GateResult(status="PASS", gate_name=self.name, details=f"All files present: {found}", duration_ms=elapsed_ms)
        return GateResult(status="FAIL", gate_name=self.name, details=f"Missing: {missing}", duration_ms=elapsed_ms)


class OutputKeywordGate(Gate):
    name = "output_keyword"
    description = "Checks that the agent's output contains required keywords."
    required = False

    def __init__(self, keywords: List[str]):
        self._keywords = keywords
        super().__init__()

    async def verify(self, workspace: str, task_description: str, agent_output: str) -> GateResult:
        start = time.time()
        lower = agent_output.lower()
        missing = [k for k in self._keywords if k.lower() not in lower]
        elapsed_ms = (time.time() - start) * 1000
        if not missing:
            return GateResult(status="PASS", gate_name=self.name, details=f"Keywords present: {self._keywords}", duration_ms=elapsed_ms)
        return GateResult(status="FAIL", gate_name=self.name, details=f"Missing keywords: {missing}", duration_ms=elapsed_ms)


@dataclass
class VerificationReport:
    task_idx: int
    task_description: str
    results: List[GateResult] = field(default_factory=list)
    total_duration_ms: float = 0.0

    @property
    def passed(self) -> bool:
        return all(
            r.passed for r in self.results if r.required
        )

    @property
    def all_required_passed(self) -> bool:
        return all(r.passed for r in self.results if r.required)

    def summary(self) -> str:
        lines = []
        for r in self.results:
            icon = "PASS" if r.passed else "FAIL"
            lines.append(f"  [{icon}] {r.gate_name} ({r.duration_ms:.0f}ms)")
            if r.details:
                lines.append(f"         {r.details[:200]}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "task_idx": self.task_idx,
            "passed": self.passed,
            "all_required_passed": self.all_required_passed,
            "total_duration_ms": self.total_duration_ms,
            "gates": [
                {"name": r.gate_name, "status": r.status, "details": r.details[:500], "duration_ms": r.duration_ms}
                for r in self.results
            ]
        }


class GateSuite:
    def __init__(self, gates: Optional[List[Gate]] = None):
        if not gates:
            self.gates = [
                TestGate(),
                LintGate(),
                TypeCheckGate(),
            ]
        else:
            self.gates = list(gates)

    @staticmethod
    def _normalize_gate_name(name: str) -> str:
        """Normalize gate name variants to internal names."""
        mapping = {
            "testsuite": "test_suite", "testgate": "test_suite",
            "test": "test_suite", "test_gate": "test_suite",
            "lintgate": "lint", "lint_gate": "lint",
            "typecheckgate": "type_check", "typecheck": "type_check",
            "type_check_gate": "type_check", "mypy": "type_check",
            "ruff": "lint",
        }
        key = name.lower().replace("-", "_").replace(" ", "_")
        return mapping.get(key, name)

    def filter_by_names(self, gate_names: Optional[List[str]] = None) -> List[Gate]:
        if not gate_names:
            return list(self.gates)
        name_map = {g.name: g for g in self.gates}
        # Support 'all' keyword plus individual names
        if "all" in gate_names:
            return list(self.gates)
        result = []
        for name in gate_names:
            normalized = self._normalize_gate_name(name)
            if normalized in name_map:
                result.append(name_map[normalized])
            elif name.startswith("file_exists:"):
                path = name[len("file_exists:"):]
                result.append(FileExistsGate([path]))
        return result

    async def run_all(self, workspace: str, task_description: str, agent_output: str, gate_names: Optional[List[str]] = None) -> VerificationReport:
        start = time.time()
        active_gates = self.filter_by_names(gate_names)
        if not active_gates:
            return VerificationReport(
                task_idx=0, task_description=task_description,
                results=[], total_duration_ms=0.0
            )
        results = await asyncio.gather(*[
            gate.verify(workspace, task_description, agent_output)
            for gate in active_gates
        ])
        elapsed = (time.time() - start) * 1000
        gate_results = list(results)
        for i, gate in enumerate(active_gates):
            if i < len(gate_results):
                gate_results[i].required = gate.required
        return VerificationReport(
            task_idx=0,
            task_description=task_description,
            results=gate_results,
            total_duration_ms=elapsed
        )
