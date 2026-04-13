import os
import pytest
from unittest.mock import patch, MagicMock
from squad_os.agents.base import BaseAgent
from squad_os.tools.registry import FileWriterTool
from squad_os.database.session import init_db
import json

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

    # Mock litellm.acompletion to avoid API calls and authentication errors
    mock_response = MagicMock()

    # First call: tool call
    mock_choice_tool = MagicMock()
    mock_message_tool = MagicMock()

    # Create a mock tool call object
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_123"
    mock_tool_call.function.name = "write_file"
    mock_tool_call.function.arguments = json.dumps({"filename": "hello_async.txt", "content": "Hello SquadOS"})

    mock_message_tool.tool_calls = [mock_tool_call]
    mock_message_tool.content = None
    mock_message_tool.model_dump.return_value = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call_123",
                "function": {"name": "write_file", "arguments": json.dumps({"filename": "hello_async.txt", "content": "Hello SquadOS"})}
            }
        ]
    }
    mock_choice_tool.message = mock_message_tool

    # Second call: final summary
    mock_choice_summary = MagicMock()
    mock_message_summary = MagicMock()
    mock_message_summary.tool_calls = None
    mock_message_summary.content = "I have written the file."
    mock_message_summary.model_dump.return_value = {
        "role": "assistant",
        "content": "I have written the file.",
        "tool_calls": None
    }
    mock_choice_summary.message = mock_message_summary

    mock_response.choices = [mock_choice_tool]
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5

    mock_response_summary = MagicMock()
    mock_response_summary.choices = [mock_choice_summary]
    mock_response_summary.usage.prompt_tokens = 20
    mock_response_summary.usage.completion_tokens = 10

    with patch('litellm.acompletion', side_effect=[mock_response, mock_response_summary]):
        result = await agent.execute_task("Write 'Hello SquadOS' to a file named 'hello_async.txt' in the workspace.", "")
        assert result is not None
        assert result["output"] == "I have written the file."

    # Locate the file in the project branch directory
    project_path = agent.active_branch.project_path
    file_path = os.path.join(project_path, "hello_async.txt")
    assert os.path.exists(file_path), f"Expected file {file_path} to exist after agent execution."

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert content == "Hello SquadOS"
