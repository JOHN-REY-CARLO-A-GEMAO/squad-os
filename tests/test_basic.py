import os

import pytest
from squad_os.agents.base import BaseAgent
from squad_os.tools.registry import FileWriterTool
from squad_os.database.session import init_db

@pytest.mark.asyncio
async def test_agent_tool():
    await init_db()
    writer = FileWriterTool()
    agent = BaseAgent(
        role="TestAgent",
        goal="Write a test file.",
        backstory="A helpful test agent.",
        tools=[writer],
        model_name="gpt-4o-mini"
    )

    result = await agent.execute_task("Write 'Hello SquadOS' to a file named 'hello_async.txt' in the workspace.", context="Testing file writing.")
    assert result is not None

    file_path = "workspace/hello_async.txt"
    assert os.path.exists(file_path), f"Expected file {file_path} to exist after agent execution."

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert content == "Hello SquadOS"
