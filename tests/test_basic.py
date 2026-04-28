import os
from unittest.mock import patch, MagicMock
import pytest
from squad_os.agents.base import BaseAgent
from squad_os.tools.registry import FileWriterTool
from squad_os.database.session import init_db

@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_agent_tool(mock_acompletion):
    # Mock LiteLLM response to avoid API key requirement
    mock_response = MagicMock()

    mock_message = MagicMock()
    mock_message.content = ""

    # Mock model_dump to return what execute_task expects
    mock_message.model_dump.return_value = {
        "content": "",
        "tool_calls": [
            {
                "id": "call_123",
                "function": {
                    "name": "write_file",
                    "arguments": '{"filename": "hello_async.txt", "content": "Hello SquadOS"}'
                }
            }
        ]
    }

    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]

    # Final response
    mock_final_response = MagicMock()
    mock_final_message = MagicMock()
    mock_final_message.content = "Task completed."
    mock_final_message.tool_calls = None
    mock_final_message.model_dump.return_value = {
        "content": "Task completed.",
        "tool_calls": None
    }

    mock_final_choice = MagicMock()
    mock_final_choice.message = mock_final_message
    mock_final_response.choices = [mock_final_choice]

    mock_acompletion.side_effect = [mock_response, mock_final_response]

    await init_db()
    writer = FileWriterTool()
    agent = BaseAgent(
        role="TestAgent",
        goal="Write a test file.",
        backstory="A helpful test agent.",
        tools=[writer],
        model_name="gpt-4o-mini"
    )

    result = await agent.execute_task("Write 'Hello SquadOS' to a file named 'hello_async.txt' in the workspace.", context="")
    assert result is not None

    # The file is written to the project branch path, not directly to workspace/
    file_path = os.path.join(agent.active_branch.project_path, "hello_async.txt")
    assert os.path.exists(file_path), f"Expected file {file_path} to exist after agent execution."

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert content == "Hello SquadOS"
