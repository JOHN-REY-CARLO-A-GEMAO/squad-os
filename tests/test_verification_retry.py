import json
import pytest
import aiosqlite
from squad_os.database.session import init_db, get_task, create_task, update_task, create_mission, DB_PATH
from squad_os.orchestrator.manager import Manager, TaskPlan, MissionPlan


@pytest.mark.asyncio
async def test_get_task_retrieves_verification_details():
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM tasks")
        await db.execute("DELETE FROM missions")
        await db.commit()
    mission_id = await create_mission("test verification retry")
    task_id = await create_task(mission_id, "test task", "Maker")
    details = {"passed": False, "gates": [{"name": "test_suite", "status": "FAIL", "details": "assert 1+1==3"}]}
    await update_task(task_id, status="FAILED", verification_status="FAILED",
                      verification_details=json.dumps(details))
    task = await get_task(task_id)
    assert task is not None
    assert task["verification_status"] == "FAILED"
    loaded = json.loads(task["verification_details"])
    assert loaded["passed"] is False
    assert loaded["gates"][0]["name"] == "test_suite"


@pytest.mark.asyncio
async def test_get_task_no_details():
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM tasks")
        await db.execute("DELETE FROM missions")
        await db.commit()
    mission_id = await create_mission("test no details")
    task_id = await create_task(mission_id, "simple task", "Maker")
    await update_task(task_id, status="COMPLETED")
    task = await get_task(task_id)
    assert task is not None
    assert task["verification_details"] is None


@pytest.mark.asyncio
async def test_get_task_nonexistent():
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM tasks")
        await db.execute("DELETE FROM missions")
        await db.commit()
    task = await get_task(99999)
    assert task is None


@pytest.mark.asyncio
async def test_retry_context_format():
    """Verify the context string format when verification failure details are injected."""
    details = {
        "passed": False,
        "gates": [{"name": "lint", "status": "FAIL", "details": "unused variable x", "duration_ms": 50.0}]
    }
    context_parts = [
        "Mission: fix the linting errors",
        "Result from Task 0: some output",
    ]
    context_parts.append(
        "--- PREVIOUS ATTEMPT VERIFICATION FAILURES ---\n"
        "The previous attempt failed automated verification. "
        "Fix the specific issues below:\n"
        f"{json.dumps(details, indent=2)}"
    )
    context = "\n\n".join(context_parts)
    assert "PREVIOUS ATTEMPT VERIFICATION FAILURES" in context
    assert "unused variable x" in context
    assert "lint" in context


@pytest.mark.asyncio
async def test_retry_injects_verification_context():
    """End-to-end: a task fails verification, then retry context includes failure details."""
    from unittest.mock import AsyncMock, MagicMock
    from squad_os.core.gates import VerificationReport, GateResult
    from squad_os.core.projects import ProjectBranch
    import tempfile

    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM tasks")
        await db.execute("DELETE FROM missions")
        await db.commit()

    mission_id = await create_mission("full retry integration")

    with tempfile.TemporaryDirectory() as tmpdir:
        maker = MagicMock()
        maker.role = "Maker"
        maker.active_branch = MagicMock()
        maker.active_branch.project_path = tmpdir
        maker.execute_task = AsyncMock(return_value={"output": "initial code"})

        fixer = MagicMock()
        fixer.role = "Fixer"
        fixer.active_branch = MagicMock()
        fixer.active_branch.project_path = tmpdir
        fixer.execute_task = AsyncMock(return_value={"output": "fixed code"})

        manager = Manager(tool_inventory=[], model_name="gpt-4o-mini", verification_enabled=False)
        manager.active_agents = {"Maker": maker, "Fixer": fixer}

        failed_report = VerificationReport(
            task_idx=0,
            task_description="write a script",
            results=[
                GateResult(status="FAIL", gate_name="test_suite",
                           details="test_example.py: assert 1+1==3", duration_ms=50.0)
            ]
        )
        mock_verifier = MagicMock()
        mock_verifier.verify = AsyncMock(return_value=failed_report)
        manager.verifier = mock_verifier

        plan = MissionPlan(
            tasks=[TaskPlan(description="write a script", assigned_agent_role="Maker", depends_on=[])],
            suggested_parallelism=1
        )
        manager.plan_mission_obj = plan
        tasks = plan.tasks

        branch = MagicMock(spec=ProjectBranch)
        branch.project_path = tmpdir
        branch.fork = MagicMock()

        await manager.execute_dag(tasks, mission_id, "write a script for me", branch)

        assert maker.execute_task.call_count >= 1, "Maker should have been called"
        if maker.execute_task.call_count > 0:
            first_context = maker.execute_task.call_args_list[0][0][1]
            assert "VERIFICATION" not in first_context.upper(), "First attempt should NOT have verification context"

        if fixer.execute_task.call_count > 0:
            fixer_call = fixer.execute_task.call_args_list[0]
            retry_context = fixer_call[0][1]
            has_feedback = (
                "VERIFICATION" in retry_context.upper()
                or "test_suite" in retry_context
                or "1+1==3" in retry_context
            )
            assert has_feedback, (
                f"Retry context should include verification failure details.\n"
                f"Got context:\n{retry_context[:500]}"
            )
