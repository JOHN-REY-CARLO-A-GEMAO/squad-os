import os
import json
import asyncio
import subprocess
from typing import Optional, List
from squad_os.tools.base import BaseTool, retry_on_failure


class EvolutionTool(BaseTool):
    name = "evolution"
    description = (
        "Self-improvement and autonomous patching system. Agents can trigger tests, "
        "analyze failures, apply fixes, and manage version-controlled changes. "
        "All autonomous changes are made on branches requiring human approval for merge."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["test", "analyze", "patch", "status", "rollback"],
                "description": "'test' to run tests, 'analyze' to diagnose failures, 'patch' to apply a fix, 'status' for branch health, 'rollback' to revert"
            },
            "target": {
                "type": "string",
                "description": "File or module path to test/patch (e.g., 'squad_os/tools/registry.py')"
            },
            "test_pattern": {
                "type": "string",
                "description": "Test pattern to run (default: 'tests/')"
            },
            "fix_description": {
                "type": "string",
                "description": "Description of the proposed fix (for patch action)"
            },
            "branch_name": {
                "type": "string",
                "description": "Branch name for autonomous changes (default: auto-generated)"
            }
        },
        "required": ["action"]
    }
    category = "system"

    def _find_tests(self, test_pattern: str) -> List[str]:
        import glob
        return glob.glob(test_pattern, recursive=True)

    async def _run_pytest(self, test_pattern: str) -> dict:
        proc = await asyncio.create_subprocess_exec(
            "python", "-m", "pytest", test_pattern, "-x", "--tb=short",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        return {
            "returncode": proc.returncode,
            "stdout": stdout.decode()[-2000:],
            "stderr": stderr.decode()[-2000:],
            "passed": proc.returncode == 0
        }

    @retry_on_failure(max_attempts=2, delay=1.0)
    async def execute(self, action: str, target: Optional[str] = None,
                      test_pattern: str = "tests/", fix_description: Optional[str] = None,
                      branch_name: Optional[str] = None) -> str:
        if action == "test":
            return await self._run_tests(test_pattern, target)
        elif action == "analyze":
            return await self._analyze(target, test_pattern)
        elif action == "patch":
            return await self._apply_patch(target, fix_description, branch_name)
        elif action == "status":
            return await self._branch_status()
        elif action == "rollback":
            return await self._rollback(branch_name)
        return f"Error: Unknown action '{action}'."

    async def _run_tests(self, test_pattern: str, target: Optional[str]) -> str:
        run_target = target or test_pattern
        result = await self._run_pytest(run_target)
        return json.dumps({
            "action": "test",
            "target": run_target,
            "passed": result["passed"],
            "returncode": result["returncode"],
            "stdout": result["stdout"][:1000],
            "stderr": result["stderr"][:500]
        }, indent=2)

    async def _analyze(self, target: Optional[str], test_pattern: str) -> str:
        analysis = {"target": target or test_pattern}

        test_result = await self._run_pytest(test_pattern)
        analysis["test_result"] = {
            "passed": test_result["passed"],
            "returncode": test_result["returncode"]
        }

        if not test_result["passed"]:
            output = test_result["stdout"] + "\n" + test_result["stderr"]
            error_lines = [l for l in output.split("\n") if "Error" in l or "FAIL" in l or "Exception" in l]
            analysis["errors"] = error_lines[:10]

            if "SyntaxError" in output:
                analysis["diagnosis"] = "Syntax error detected. Likely missing import, typo, or invalid syntax."
                analysis["severity"] = "high"
            elif "ImportError" in output or "ModuleNotFoundError" in output:
                analysis["diagnosis"] = "Missing import or module not installed."
                analysis["severity"] = "high"
            elif "AssertionError" in output or "assert" in output:
                analysis["diagnosis"] = "Test assertion failed. Logic error in implementation."
                analysis["severity"] = "medium"
            elif "KeyError" in output or "AttributeError" in output:
                analysis["diagnosis"] = "Missing key or attribute. Likely API mismatch."
                analysis["severity"] = "medium"
            elif "TimeoutError" in output or "timeout" in output:
                analysis["diagnosis"] = "Operation timed out. May need longer timeout or optimization."
                analysis["severity"] = "low"
            else:
                analysis["diagnosis"] = "Unknown error. Manual inspection recommended."
                analysis["severity"] = "medium"
        else:
            analysis["diagnosis"] = "All tests pass. No issues detected."
            analysis["severity"] = "none"

        return json.dumps(analysis, indent=2)

    async def _apply_patch(self, target: Optional[str], fix_description: Optional[str],
                           branch_name: Optional[str]) -> str:
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        branch = branch_name or f"auto-fix/{timestamp}"

        try:
            git_result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, timeout=10
            )
            if git_result.returncode != 0:
                return "Not a git repository. Cannot create patch branch."

            subprocess.run(["git", "checkout", "-b", branch], capture_output=True, text=True, timeout=10)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return "Git not available. Cannot create patch branch."

        return json.dumps({
            "action": "patch",
            "status": "branch_created",
            "branch": branch,
            "target": target or "auto-detected",
            "fix_description": fix_description or "Autonomous fix",
            "next_steps": [
                "1. Run 'git diff' to review changes",
                f"2. Test with: pytest {target or 'tests/'}",
                "3. Request human approval before merging",
                f"4. Merge: git checkout main && git merge {branch}"
            ]
        }, indent=2)

    async def _branch_status(self) -> str:
        try:
            result = subprocess.run(
                ["git", "branch", "--list"],
                capture_output=True, text=True, timeout=10
            )
            branches = [b.strip() for b in result.stdout.split("\n") if b.strip()]
            active = [b for b in branches if b.startswith("auto-fix/")]

            result = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True, text=True, timeout=10
            )
            changes = [l.strip() for l in result.stdout.split("\n") if l.strip()]

            return json.dumps({
                "total_branches": len(branches),
                "auto_fix_branches": len(active),
                "auto_fix_list": active,
                "uncommitted_changes": len(changes),
                "changes": changes[:20]
            }, indent=2)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return json.dumps({"error": "Git not available or not a git repository."}, indent=2)

    async def _rollback(self, branch_name: Optional[str]) -> str:
        if not branch_name:
            return "Error: 'branch_name' is required for rollback."
        try:
            result = subprocess.run(
                ["git", "branch", "--list", branch_name],
                capture_output=True, text=True, timeout=10
            )
            if branch_name not in result.stdout:
                return f"Branch '{branch_name}' not found."

            subprocess.run(["git", "checkout", "main"], capture_output=True, text=True, timeout=10)
            subprocess.run(["git", "branch", "-D", branch_name], capture_output=True, text=True, timeout=10)
            return json.dumps({
                "action": "rollback",
                "status": "rolled_back",
                "branch": branch_name,
                "message": f"Branch '{branch_name}' deleted. Switched to main."
            }, indent=2)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return "Git not available."
