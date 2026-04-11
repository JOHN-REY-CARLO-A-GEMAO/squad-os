import os
import json
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

    # Mock litellm.acompletion to avoid API calls and auth errors
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_123"
    mock_tool_call.function.name = "write_file"
    mock_tool_call.function.arguments = json.dumps({"filename": "hello_async.txt", "content": "Hello SquadOS"})

    mock_response_1 = MagicMock()
    mock_response_1.choices = [MagicMock(message=MagicMock(tool_calls=[mock_tool_call], content=None))]
    mock_response_1.choices[0].message.dict.return_value = {"tool_calls": [mock_tool_call], "content": None}

    mock_response_nudge = MagicMock()
    mock_response_nudge.choices = [MagicMock(message=MagicMock(tool_calls=None, content="Summary of work..."))]
    mock_response_nudge.choices[0].message.dict.return_value = {"tool_calls": None, "content": "Summary of work..."}
    mock_response_nudge.usage.prompt_tokens = 5
    mock_response_nudge.usage.completion_tokens = 2

    mock_response_2 = MagicMock()
    mock_response_2.choices = [MagicMock(message=MagicMock(tool_calls=None, content="File written successfully."))]
    mock_response_2.choices[0].message.dict.return_value = {"tool_calls": None, "content": "File written successfully."}
    mock_response_2.usage.prompt_tokens = 10
    mock_response_2.usage.completion_tokens = 5

    with patch("litellm.acompletion", side_effect=[mock_response_1, mock_response_nudge]):
        result = await agent.execute_task("Write 'Hello SquadOS' to a file named 'hello_async.txt' in the workspace.", context="")

    assert result is not None
    assert result["output"] == "Summary of work..."

    # Locate artifact using project path from agent's active branch
    file_path = os.path.join(agent.active_branch.project_path, "hello_async.txt")
    assert os.path.exists(file_path), f"Expected file {file_path} to exist after agent execution."

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert content == "Hello SquadOS"
