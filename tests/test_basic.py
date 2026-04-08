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

    # Mocking litellm.acompletion to avoid API calls and auth errors
    from unittest.mock import patch, MagicMock

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[0].message.content = "I have written the file."
    mock_response.choices[0].message.tool_calls = [
        MagicMock(id="1", function=MagicMock(name="write_file", arguments='{"filename": "hello_async.txt", "content": "Hello SquadOS"}'))
    ]
    mock_response.choices[0].message.dict.return_value = {
        "content": "I have written the file.",
        "tool_calls": [
            {"id": "1", "function": {"name": "write_file", "arguments": '{"filename": "hello_async.txt", "content": "Hello SquadOS"}'}}
        ]
    }
    mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)

    mock_final_response = MagicMock()
    mock_final_response.choices = [MagicMock()]
    mock_final_response.choices[0].message = MagicMock()
    mock_final_response.choices[0].message.content = "Summary: Task completed."
    mock_final_response.choices[0].message.tool_calls = None
    mock_final_response.choices[0].message.dict.return_value = {"content": "Summary: Task completed.", "tool_calls": None}
    mock_final_response.usage = MagicMock(prompt_tokens=20, completion_tokens=10)

    mock_nudge_response = MagicMock()
    mock_nudge_response.choices = [MagicMock()]
    mock_nudge_response.choices[0].message = MagicMock()
    mock_nudge_response.choices[0].message.content = "Summary: Task completed after nudge."
    mock_nudge_response.choices[0].message.tool_calls = None
    mock_nudge_response.choices[0].message.dict.return_value = {"content": "Summary: Task completed after nudge.", "tool_calls": None}
    mock_nudge_response.usage = MagicMock(prompt_tokens=30, completion_tokens=15)

    with patch("litellm.acompletion", side_effect=[mock_response, mock_nudge_response, mock_final_response]):
        result = await agent.execute_task("Write 'Hello SquadOS' to a file named 'hello_async.txt' in the workspace.", context="")
        assert result is not None

    # Find the file in the project branch directory
    branch_dir = agent.active_branch.project_path
    file_path = os.path.join(branch_dir, "hello_async.txt")
    assert os.path.exists(file_path), f"Expected file {file_path} to exist after agent execution."

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert content == "Hello SquadOS"
