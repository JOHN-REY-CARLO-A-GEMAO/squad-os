import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock
from squad_os.orchestrator.manager import Manager, TaskPlan, MissionPlan
from squad_os.agents.base import BaseAgent

class TestManagerParallel(unittest.IsolatedAsyncioTestCase):
    async def test_parallel_execution_flow(self):
        # Mock agents
        agent1 = MagicMock(spec=BaseAgent)
        agent1.role = "Agent1"
        agent1.tools = []
        agent1.execute_task = AsyncMock(return_value={"output": "Result 1", "prompt_tokens": 10, "completion_tokens": 10, "cost_usd": 0.01, "execution_ms": 100})

        agent2 = MagicMock(spec=BaseAgent)
        agent2.role = "Agent2"
        agent2.tools = []
        agent2.execute_task = AsyncMock(return_value={"output": "Result 2", "prompt_tokens": 10, "completion_tokens": 10, "cost_usd": 0.01, "execution_ms": 100})

        manager = Manager(agents=[agent1, agent2])

        # Mock planning to return a fixed plan
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

        result = await manager.run_mission("Test Goal")

        # Verify that both agents were called
        agent1.execute_task.assert_called_once()
        agent2.execute_task.assert_called_once()

        self.assertIn("Task task_1: Result 1", result)
        self.assertIn("Task task_2: Result 2", result)

if __name__ == "__main__":
    unittest.main()
