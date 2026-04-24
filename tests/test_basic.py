import os
import pytest
from squad_os.agents.base import BaseAgent
from squad_os.tools.registry import FileWriterTool
from squad_os.database.session import init_db
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
async def test_agent_tool():
    # Mock litellm.acompletion
    # First response: tool call
    mock_response_1 = MagicMock()
    mock_response_1.choices = [MagicMock()]
    mock_response_1.choices[0].message.role = "assistant"
    mock_response_1.choices[0].message.content = "I will write the file now."

    # BaseAgent uses resp_dict = resp_msg.model_dump() or .dict()
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_123"
    mock_tool_call.function.name = "write_file"
    mock_tool_call.function.arguments = '{"filename": "hello_async.txt", "content": "Hello SquadOS"}'

    mock_response_1.choices[0].message.tool_calls = [mock_tool_call]
    # Simulate both model_dump and dict just in case
    mock_response_1.choices[0].message.model_dump.return_value = {
        "role": "assistant",
        "content": "I will write the file now.",
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
    mock_response_1.choices[0].message.dict.return_value = mock_response_1.choices[0].message.model_dump.return_value

    # Second response: final summary (after nudge)
    mock_response_2 = MagicMock()
    mock_response_2.choices = [MagicMock()]
    mock_response_2.choices[0].message.role = "assistant"
    mock_response_2.choices[0].message.content = "Summary: I wrote the file."
    mock_response_2.choices[0].message.tool_calls = None
    mock_response_2.choices[0].message.model_dump.return_value = {
        "role": "assistant",
        "content": "Summary: I wrote the file.",
        "tool_calls": None
    }
    mock_response_2.choices[0].message.dict.return_value = mock_response_2.choices[0].message.model_dump.return_value
    mock_response_2.usage.prompt_tokens = 10
    mock_response_2.usage.completion_tokens = 5

    mock_responses = [mock_response_1, mock_response_2]

    with patch('litellm.acompletion', side_effect=mock_responses):
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
        assert "Summary" in result["output"]

        branch_id = agent.active_branch.task_id
        actual_file_path = os.path.join("workspace", "projects", branch_id, "hello_async.txt")

        assert os.path.exists(actual_file_path), f"Expected file {actual_file_path} to exist."

        with open(actual_file_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert content == "Hello SquadOS"
