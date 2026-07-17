import os
import tempfile
import pytest
from squad_os.core.gates import (
    GateResult, TestGate, LintGate, TypeCheckGate,
    FileExistsGate, OutputKeywordGate, GateSuite, VerificationReport
)
from squad_os.agents.verifier import VerifierAgent


class TestGateResult:
    def test_passed_property(self):
        assert GateResult(status="PASS", gate_name="test").passed
        assert not GateResult(status="FAIL", gate_name="test").passed
        assert not GateResult(status="ERROR", gate_name="test").passed

    def test_repr(self):
        r = GateResult(status="PASS", gate_name="lint", details="No errors", duration_ms=10.5)
        assert r.gate_name == "lint"
        assert r.details == "No errors"


class TestFileExistsGate:
    @pytest.mark.asyncio
    async def test_all_files_present(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "test.py"), "w").close()
            open(os.path.join(tmpdir, "test.txt"), "w").close()
            gate = FileExistsGate(required_files=["test.py", "test.txt"])
            result = await gate.verify(tmpdir, "", "")
            assert result.status == "PASS"

    @pytest.mark.asyncio
    async def test_missing_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gate = FileExistsGate(required_files=["missing.py"])
            result = await gate.verify(tmpdir, "", "")
            assert result.status == "FAIL"
            assert "missing.py" in result.details


class TestOutputKeywordGate:
    @pytest.mark.asyncio
    async def test_keywords_present(self):
        gate = OutputKeywordGate(keywords=["success", "completed"])
        result = await gate.verify("", "", "The task was completed successfully")
        assert result.status == "PASS"

    @pytest.mark.asyncio
    async def test_keywords_missing(self):
        gate = OutputKeywordGate(keywords=["error", "exception"])
        result = await gate.verify("", "", "Everything completed successfully")
        assert result.status == "FAIL"


class TestTestGate:
    @pytest.mark.asyncio
    async def test_no_test_files_skips(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gate = TestGate()
            result = await gate.verify(tmpdir, "", "")
            assert result.status == "PASS"
            assert "skipped" in result.details.lower()

    @pytest.mark.asyncio
    async def test_with_test_file(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            test_dir = os.path.join(tmpdir, "tests")
            os.makedirs(test_dir)
            test_file = os.path.join(test_dir, "test_example.py")
            with open(test_file, "w") as f:
                f.write("def test_pass():\n    assert 1 + 1 == 2\n")
            gate = TestGate()
            result = await gate.verify(tmpdir, "", "")
            assert result.status == "PASS"

    @pytest.mark.asyncio
    async def test_failing_test(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            test_dir = os.path.join(tmpdir, "tests")
            os.makedirs(test_dir)
            test_file = os.path.join(test_dir, "test_fail.py")
            with open(test_file, "w") as f:
                f.write("def test_fail():\n    assert 1 + 1 == 3\n")
            gate = TestGate()
            result = await gate.verify(tmpdir, "", "")
            assert result.status == "FAIL"


class TestGateSuite:
    @pytest.mark.asyncio
    async def test_empty_suite_loads_defaults(self):
        suite = GateSuite(gates=[])
        with tempfile.TemporaryDirectory() as tmpdir:
            report = await suite.run_all(tmpdir, "task", "output")
            assert report.passed
            assert len(report.results) == 3

    @pytest.mark.asyncio
    async def test_all_gates_pass(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            suite = GateSuite(gates=[
                FileExistsGate(required_files=[]),
                OutputKeywordGate(keywords=["done"]),
            ])
            report = await suite.run_all(tmpdir, "task", "task done")
            assert report.passed

    @pytest.mark.asyncio
    async def test_any_gate_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            suite = GateSuite(gates=[
                FileExistsGate(required_files=["nonexistent.py"]),
            ])
            report = await suite.run_all(tmpdir, "task", "done")
            assert not report.passed

    @pytest.mark.asyncio
    async def test_verification_report_to_dict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            suite = GateSuite(gates=[FileExistsGate(required_files=[])])
            report = await suite.run_all(tmpdir, "task", "done")
            d = report.to_dict()
            assert "task_idx" in d
            assert "passed" in d
            assert "gates" in d
            assert isinstance(d["gates"], list)


class TestVerifierAgent:
    @pytest.mark.asyncio
    async def test_verify_passes_with_no_gates(self):
        verifier = VerifierAgent(gates=[])
        with tempfile.TemporaryDirectory() as tmpdir:
            report = await verifier.verify(tmpdir, "test task", "output")
            assert report.passed

    @pytest.mark.asyncio
    async def test_verify_file_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "result.txt"), "w").close()
            verifier = VerifierAgent(gates=[FileExistsGate(required_files=["result.txt"])])
            report = await verifier.verify(tmpdir, "create result.txt", "done")
            assert report.passed

    @pytest.mark.asyncio
    async def test_verify_file_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            verifier = VerifierAgent(gates=[FileExistsGate(required_files=["missing.txt"])])
            report = await verifier.verify(tmpdir, "create missing.txt", "done")
            assert not report.all_required_passed


class TestVerificationReport:
    def test_summary_format(self):
        report = VerificationReport(
            task_idx=0,
            task_description="test",
            results=[
                GateResult(status="PASS", gate_name="test_suite", details="ok", duration_ms=10.0),
                GateResult(status="FAIL", gate_name="lint", details="error", duration_ms=5.0),
            ]
        )
        summary = report.summary()
        assert "[PASS]" in summary
        assert "[FAIL]" in summary
        assert "test_suite" in summary
        assert "lint" in summary
