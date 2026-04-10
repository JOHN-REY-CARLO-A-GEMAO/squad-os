import os

import pytest
from unittest.mock import patch, MagicMock
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

    # Mock litellm.acompletion to avoid API calls and authentication errors
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()

    # First call: agent decides to use tool
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_123"
    mock_tool_call.function.name = "write_file"
    mock_tool_call.function.arguments = '{"filename": "hello_async.txt", "content": "Hello SquadOS"}'

    mock_message.tool_calls = [mock_tool_call]
    mock_message.content = "I will write the file."
    mock_choice.message = mock_message

    # Second call: agent acknowledges tool output
    mock_response_2 = MagicMock()
    mock_choice_2 = MagicMock()
    mock_message_2 = MagicMock()
    mock_message_2.tool_calls = None
    mock_message_2.content = "File written."
    # mock_message_2.dict.return_value = {"tool_calls": None} # Memory says this might be needed

    mock_choice_2.message = mock_message_2
    mock_response_2.choices = [mock_choice_2]
    mock_response_2.usage.prompt_tokens = 10
    mock_response_2.usage.completion_tokens = 10

    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 10

    with patch("litellm.acompletion", side_effect=[mock_response, mock_response_2]):
        result = await agent.execute_task("Write 'Hello SquadOS' to a file named 'hello_async.txt' in the workspace.", context="")
        assert result is not None

    file_path = "workspace/hello_async.txt"
    assert os.path.exists(file_path), f"Expected file {file_path} to exist after agent execution."

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert content == "Hello SquadOS"
