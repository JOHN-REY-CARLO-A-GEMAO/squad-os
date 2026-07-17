import os
import json
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from squad_os.agents.base import BaseAgent
from squad_os.core.projects import ProjectBranch
from squad_os.orchestrator.manager import Manager, TaskPlan, MissionPlan
from squad_os.tools.registry import FileWriterTool, ReadFileTool
from squad_os.database.session import init_db, create_mission, DB_PATH
import aiosqlite


class TestTaskWorkspaceAttribute:
    def test_task_workspace_defaults_to_none(self):
        agent = BaseAgent(role="TestAgent", goal="test", backstory="test", tools=[])
        assert agent.task_workspace is None

    def test_task_workspace_can_be_set(self):
        agent = BaseAgent(role="TestAgent", goal="test", backstory="test", tools=[])
        agent.task_workspace = "/tmp/isolated"
        assert agent.task_workspace == "/tmp/isolated"


class TestToolWorkspaceInjection:
    @pytest.mark.asyncio
    async def test_tools_get_task_workspace_when_set(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            branch_root = os.path.join(tmpdir, "branch")
            task_dir = os.path.join(tmpdir, "task_0")

            branch = ProjectBranch("test-branch", base_dir=tmpdir)
            branch.project_path = branch_root
            branch.visuals_path = os.path.join(branch_root, "visuals")

            writer = FileWriterTool()
            agent = BaseAgent(
                role="TestAgent", goal="test", backstory="test",
                tools=[writer], model_name="gpt-4o-mini"
            )
            agent.active_branch = branch
            agent.task_workspace = task_dir

            with patch("litellm.acompletion", AsyncMock(return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    model_dump=MagicMock(return_value={"content": "done", "tool_calls": None})
                ))]
            ))):
                await agent.execute_task("test task", "context")

            assert writer.workspace == task_dir, (
                f"FileWriterTool workspace should be {task_dir}, got {writer.workspace}"
            )

    @pytest.mark.asyncio
    async def test_tools_fall_back_to_active_branch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            branch = ProjectBranch("test-branch", base_dir=tmpdir)
            branch.fork()

            writer = FileWriterTool()
            agent = BaseAgent(
                role="TestAgent", goal="test", backstory="test",
                tools=[writer], model_name="gpt-4o-mini"
            )
            agent.active_branch = branch

            with patch("litellm.acompletion", AsyncMock(return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    model_dump=MagicMock(return_value={"content": "done", "tool_calls": None})
                ))]
            ))):
                await agent.execute_task("test task", "context")

            assert writer.workspace == branch.project_path, (
                f"Without task_workspace, tool should get {branch.project_path}, "
                f"got {writer.workspace}"
            )


class TestParallelTaskIsolation:
    @pytest.mark.asyncio
    async def test_parallel_tasks_write_to_different_dirs(self):
        """Two parallel tasks writing the same filename should not collide."""
        await init_db()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM tasks")
            await db.execute("DELETE FROM missions")
            await db.commit()

        mission_id = await create_mission("test parallel isolation")

        with tempfile.TemporaryDirectory() as tmpdir:
            branch = ProjectBranch("isolation-test", base_dir=tmpdir)
            branch.fork()
            branch_root = branch.project_path

            maker_a = MagicMock()
            maker_a.role = "MakerA"
            maker_a.active_branch = branch
            maker_a.task_workspace = None
            maker_a.execute_task = AsyncMock(return_value={"output": "wrote file a"})

            maker_b = MagicMock()
            maker_b.role = "MakerB"
            maker_b.active_branch = branch
            maker_b.task_workspace = None
            maker_b.execute_task = AsyncMock(return_value={"output": "wrote file b"})

            manager = Manager(tool_inventory=[], model_name="gpt-4o-mini", verification_enabled=False)
            manager.active_agents = {"MakerA": maker_a, "MakerB": maker_b}

            plan = MissionPlan(
                tasks=[
                    TaskPlan(description="write file a", assigned_agent_role="MakerA", depends_on=[]),
                    TaskPlan(description="write file b", assigned_agent_role="MakerB", depends_on=[]),
                ],
                suggested_parallelism=2
            )
            manager.plan_mission_obj = plan
            tasks = plan.tasks

            await manager.execute_dag(tasks, mission_id, "test parallel", branch)

            task_0_dir = os.path.join(branch_root, "task_0")
            task_1_dir = os.path.join(branch_root, "task_1")

            assert os.path.isdir(task_0_dir), f"Task 0 workspace should exist: {task_0_dir}"
            assert os.path.isdir(task_1_dir), f"Task 1 workspace should exist: {task_1_dir}"

            assert task_0_dir != task_1_dir, "Task workspaces must be different directories"

            assert maker_a.task_workspace == task_0_dir, (
                f"MakerA should have workspace {task_0_dir}, got {maker_a.task_workspace}"
            )
            assert maker_b.task_workspace == task_1_dir, (
                f"MakerB should have workspace {task_1_dir}, got {maker_b.task_workspace}"
            )


class TestCommitAcrossTaskDirs:
    @pytest.mark.asyncio
    async def test_commit_finds_files_in_task_subdirs(self):
        """CommitProjectTool scans the branch root with os.walk, which
        naturally finds files inside task_N/ subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            branch = ProjectBranch("commit-test", base_dir=tmpdir)
            branch.fork()
            branch_root = branch.project_path

            task_0_dir = os.path.join(branch_root, "task_0")
            os.makedirs(task_0_dir, exist_ok=True)

            file_a = os.path.join(task_0_dir, "output.py")
            with open(file_a, "w") as f:
                f.write("print('hello')")

            file_b = os.path.join(task_0_dir, "data.json")
            with open(file_b, "w") as f:
                f.write('{"key": "value"}')

            final_outputs_dir = os.path.join(tmpdir, "final_outputs")
            artifacts = ["output.py", "data.json"]
            committed = await branch.commit(artifacts)

            assert len(committed) == 2, f"Expected 2 committed files, got {len(committed)}"
            for path in committed:
                assert os.path.exists(path), f"Committed file does not exist: {path}"
                assert "commit-test" in path, f"Commit should prefix with task_id"

    @pytest.mark.asyncio
    async def test_commit_collects_from_multiple_task_dirs(self):
        """Commit collects files from multiple task_N/ directories without collision."""
        with tempfile.TemporaryDirectory() as tmpdir:
            branch = ProjectBranch("multi-task", base_dir=tmpdir)
            branch.fork()
            branch_root = branch.project_path

            for i in range(2):
                task_dir = os.path.join(branch_root, f"task_{i}")
                os.makedirs(task_dir, exist_ok=True)
                with open(os.path.join(task_dir, "report.md"), "w") as f:
                    f.write(f"# Report from Task {i}")

            artifacts = ["report.md"]
            committed = await branch.commit(artifacts)

            assert len(committed) == 2, (
                f"Expected 2 committed files (one from each task), got {len(committed)}: {committed}"
            )


class TestVerifyWorkspaceIsolation:
    @pytest.mark.asyncio
    async def test_verifier_gets_task_workspace(self):
        """The VerifierAgent should use the per-task workspace."""
        await init_db()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM tasks")
            await db.execute("DELETE FROM missions")
            await db.commit()

        mission_id = await create_mission("test verifier isolation")

        with tempfile.TemporaryDirectory() as tmpdir:
            branch = ProjectBranch("verify-test", base_dir=tmpdir)
            branch.fork()
            branch_root = branch.project_path

            from squad_os.core.gates import VerificationReport, GateResult
            from unittest.mock import AsyncMock, MagicMock

            maker = MagicMock()
            maker.role = "Maker"
            maker.active_branch = branch
            maker.task_workspace = None
            maker.execute_task = AsyncMock(return_value={"output": "done"})

            manager = Manager(tool_inventory=[], model_name="gpt-4o-mini", verification_enabled=False)
            manager.active_agents = {"Maker": maker}

            pass_report = VerificationReport(
                task_idx=0, task_description="test",
                results=[GateResult(status="PASS", gate_name="check", details="ok", duration_ms=1.0)]
            )
            mock_verifier = MagicMock()
            mock_verifier.verify = AsyncMock(return_value=pass_report)
            manager.verifier = mock_verifier

            plan = MissionPlan(
                tasks=[TaskPlan(description="test", assigned_agent_role="Maker", depends_on=[])],
                suggested_parallelism=1
            )
            manager.plan_mission_obj = plan
            tasks = plan.tasks

            await manager.execute_dag(tasks, mission_id, "test verifier", branch)

            expected_workspace = os.path.join(branch_root, "task_0")
            assert mock_verifier.verify.call_count >= 1, "Verifier should have been called"
            if mock_verifier.verify.call_count > 0:
                call_kwargs = mock_verifier.verify.call_args_list[0][1]
                actual_workspace = call_kwargs.get("workspace", "")
                assert actual_workspace == expected_workspace, (
                    f"Verifier should receive task workspace '{expected_workspace}', "
                    f"got '{actual_workspace}'"
                )
