import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock
from squad_os.orchestrator.manager import Manager, TaskPlan, MissionPlan
from squad_os.agents.base import BaseAgent

class TestManagerFailure(unittest.IsolatedAsyncioTestCase):
    async def test_task_failure_propagation(self):
        # Mock agents
        agent1 = MagicMock(spec=BaseAgent)
        agent1.role = "Agent1"
        agent1.tools = []
        # Task 1 will fail after retries
        agent1.execute_task = AsyncMock(return_value={"error": "Simulated failure", "execution_ms": 100})

        agent2 = MagicMock(spec=BaseAgent)
        agent2.role = "Agent2"
        agent2.tools = []
        agent2.execute_task = AsyncMock(return_value={"output": "Should not run", "execution_ms": 100})

        manager = Manager(agents=[agent1, agent2])
        manager.max_retries = 1 # speed up test

        # Mock planning: Task 2 depends on Task 1
        mission_plan = MissionPlan(tasks=[
            TaskPlan(task_id="task_1", description="Task 1", assigned_agent_role="Agent1", depends_on=[]),
            TaskPlan(task_id="task_2", description="Task 2", assigned_agent_role="Agent2", depends_on=["task_1"])
        ])
        manager.plan_mission = AsyncMock(return_value=mission_plan)

        # Mock DB calls
        import squad_os.orchestrator.manager as manager_mod
        manager_mod.create_mission = AsyncMock(return_value=1)
        manager_mod.create_task = AsyncMock(return_value=1)
        manager_mod.update_task = AsyncMock()
        manager_mod.update_mission = AsyncMock()
        manager_mod.create_post_mortem = AsyncMock()

        result = await manager.run_mission("Failure Test")

        # Verify that agent1 was called twice (initial + 1 retry)
        self.assertEqual(agent1.execute_task.call_count, 2)
        # Verify that agent2 was never called
        agent2.execute_task.assert_not_called()

        # Check result summary
        self.assertIn("Task task_1: FAILED: Simulated failure", result)
        self.assertIn("Task task_2: SKIPPED: Dependency task_1 failed", result)

if __name__ == "__main__":
    unittest.main()
