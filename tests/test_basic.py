import os
import json
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
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "I have written the file."

    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_123"
    mock_tool_call.function.name = "write_file"
    mock_tool_call.function.arguments = json.dumps({"filename": "hello_async.txt", "content": "Hello SquadOS"})

    mock_response.choices[0].message.tool_calls = [mock_tool_call]
    mock_response.choices[0].message.dict.return_value = {
        "tool_calls": [
            {
                "id": "call_123",
                "function": {"name": "write_file", "arguments": json.dumps({"filename": "hello_async.txt", "content": "Hello SquadOS"})}
            }
        ],
        "content": "I have written the file."
    }
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5


    # Final response to terminate the loop
    mock_final_response = MagicMock()
    mock_final_response.choices = [MagicMock()]
    mock_final_response.choices[0].message.content = "Task complete."
    mock_final_response.choices[0].message.dict.return_value = {"tool_calls": None, "content": "Task complete."}
    mock_final_response.usage.prompt_tokens = 5
    mock_final_response.usage.completion_tokens = 2

    with patch("litellm.acompletion", side_effect=[mock_response, mock_final_response]):
        result = await agent.execute_task("Write 'Hello SquadOS' to a file named 'hello_async.txt' in the workspace.", context="")

    assert result is not None

    # In BaseAgent, tool.workspace is set to active_branch.project_path
    file_path = os.path.join(agent.active_branch.project_path, "hello_async.txt")
    assert os.path.exists(file_path), f"Expected file {file_path} to exist after agent execution."

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert content == "Hello SquadOS"
