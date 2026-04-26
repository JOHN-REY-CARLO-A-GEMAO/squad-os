import os
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
import json
from squad_os.agents.base import BaseAgent
from squad_os.tools.registry import FileWriterTool
from squad_os.database.session import init_db

@pytest.mark.asyncio
async def test_agent_tool():
    await init_db()
    writer = FileWriterTool()

    # Setup mocks for litellm.acompletion
    # First call returns a tool call
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_123"
    mock_tool_call.function.name = "write_file"
    mock_tool_call.function.arguments = json.dumps({"filename": "hello_async.txt", "content": "Hello SquadOS"})

    mock_resp_msg_1 = MagicMock()
    mock_resp_msg_1.tool_calls = [mock_tool_call]
    mock_resp_msg_1.content = None
    # BaseAgent expects either a dict or an object with model_dump/dict
    mock_resp_msg_1.model_dump.return_value = {"tool_calls": [{"id": "call_123", "function": {"name": "write_file", "arguments": mock_tool_call.function.arguments}}], "content": None}

    mock_response_1 = MagicMock()
    mock_response_1.choices = [MagicMock(message=mock_resp_msg_1)]
    mock_response_1.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)

    # Second call returns a final summary
    mock_resp_msg_2 = MagicMock()
    mock_resp_msg_2.tool_calls = None
    mock_resp_msg_2.content = "I have written the file."
    mock_resp_msg_2.model_dump.return_value = {"tool_calls": None, "content": "I have written the file."}

    mock_response_2 = MagicMock()
    mock_response_2.choices = [MagicMock(message=mock_resp_msg_2)]
    mock_response_2.usage = MagicMock(prompt_tokens=20, completion_tokens=10, total_tokens=30)

    mock_acompletion = AsyncMock(side_effect=[mock_response_1, mock_response_2, mock_response_2, mock_response_2])

    with patch("litellm.acompletion", mock_acompletion):
        agent = BaseAgent(
            role="TestAgent",
            goal="Write a test file.",
            backstory="A helpful test agent.",
            tools=[writer],
            model_name="gpt-4o-mini"
        )

        result = await agent.execute_task("Write 'Hello SquadOS' to a file named 'hello_async.txt' in the workspace.", context="")

    assert result is not None
    assert result["output"] == "I have written the file."

    # Verify that the file was created in the branch's project path
    assert agent.active_branch is not None
    file_path = os.path.join(agent.active_branch.project_path, "hello_async.txt")

    assert os.path.exists(file_path), f"Expected file {file_path} to exist."

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert content == "Hello SquadOS"
