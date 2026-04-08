import os
from unittest.mock import patch, MagicMock

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

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()

    mock_message.content = "I have written the file."
    mock_message.tool_calls = [
        MagicMock(
            id="call_1",
            function=MagicMock(
                name="write_file",
                arguments='{"filename": "hello_async.txt", "content": "Hello SquadOS"}'
            )
        )
    ]
    # Handle both object and dict access if needed by BaseAgent
    mock_message.dict.return_value = {
        "content": "I have written the file.",
        "tool_calls": [
            {
                "id": "call_1",
                "function": {
                    "name": "write_file",
                    "arguments": '{"filename": "hello_async.txt", "content": "Hello SquadOS"}'
                }
            }
        ]
    }

    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 20

    # Mock the second call to return final summary
    mock_response_summary = MagicMock()
    mock_choice_summary = MagicMock()
    mock_message_summary = MagicMock()
    mock_message_summary.content = "Final summary: File written."
    mock_message_summary.tool_calls = None
    mock_message_summary.dict.return_value = {
        "content": "Final summary: File written.",
        "tool_calls": None
    }
    mock_choice_summary.message = mock_message_summary
    mock_response_summary.choices = [mock_choice_summary]
    mock_response_summary.usage.prompt_tokens = 5
    mock_response_summary.usage.completion_tokens = 10

    with patch("litellm.acompletion", side_effect=[mock_response, mock_response_summary]):
        result = await agent.execute_task("Write 'Hello SquadOS' to a file named 'hello_async.txt' in the workspace.", context="")
    assert result is not None

    # In BaseAgent, files are written to agent.active_branch.project_path
    file_path = os.path.join(agent.active_branch.project_path, "hello_async.txt")
    assert os.path.exists(file_path), f"Expected file {file_path} to exist after agent execution."

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert content == "Hello SquadOS"
