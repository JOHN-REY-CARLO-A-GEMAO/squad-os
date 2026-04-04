import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import litellm
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

    # Mock LiteLLM to avoid real API calls
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.content = "I have written the file."
    mock_message.tool_calls = [
        MagicMock(
            id="call_123",
            function=MagicMock(
                name="write_file",
                arguments='{"filename": "hello_async.txt", "content": "Hello SquadOS"}'
            )
        )
    ]
    # To handle the .dict() call if needed or the direct access
    mock_message.dict.return_value = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "write_file",
                    "arguments": '{"filename": "hello_async.txt", "content": "Hello SquadOS"}'
                }
            }
        ]
    }

    # Second response to finish the loop
    mock_response_final = MagicMock()
    mock_choice_final = MagicMock()
    mock_message_final = MagicMock()
    mock_message_final.content = "Task complete."
    mock_message_final.tool_calls = None
    mock_message_final.dict.return_value = {
        "role": "assistant",
        "content": "Task complete.",
        "tool_calls": None
    }
    mock_choice_final.message = mock_message_final
    mock_response_final.choices = [mock_choice_final]
    mock_response_final.usage.prompt_tokens = 10
    mock_response_final.usage.completion_tokens = 5

    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5

    with patch('litellm.acompletion', new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.side_effect = [mock_response, mock_response_final]

        result = await agent.execute_task(
            "Write 'Hello SquadOS' to a file named 'hello_async.txt' in the workspace.",
            "Context: Testing agent task execution."
        )

    assert result is not None
    assert result["output"] == "Task complete."

    # The agent creates a project branch, so we need to check there
    branch_path = agent.active_branch.project_path
    file_path = os.path.join(branch_path, "hello_async.txt")

    assert os.path.exists(file_path), f"Expected file {file_path} to exist after agent execution."

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert content == "Hello SquadOS"
