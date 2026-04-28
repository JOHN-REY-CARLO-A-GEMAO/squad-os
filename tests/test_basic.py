import os
import asyncio
from unittest.mock import patch, MagicMock

import pytest
from squad_os.agents.base import BaseAgent
from squad_os.tools.registry import FileWriterTool
from squad_os.database.session import init_db

@pytest.mark.asyncio
async def test_agent_tool():
    os.environ["OPENAI_API_KEY"] = "sk-dummy"
    await init_db()

    # Mock litellm.acompletion to avoid needing an API key
    mock_tool_call = MagicMock()
    mock_tool_call.function.name = "write_file"
    mock_tool_call.function.arguments = '{"filename": "hello_async.txt", "content": "Hello SquadOS"}'
    mock_tool_call.id = "call_123"

    mock_response_tool = MagicMock()
    mock_response_tool.choices[0].message.tool_calls = [mock_tool_call]
    mock_response_tool.choices[0].message.content = None

    mock_response_text = MagicMock()
    mock_response_text.choices[0].message.tool_calls = None
    mock_response_text.choices[0].message.content = "I have written the file."
    mock_response_text.usage.prompt_tokens = 10
    mock_response_text.usage.completion_tokens = 5

    responses = [mock_response_tool, mock_response_text]
    response_idx = 0

    async def mock_acompletion(*args, **kwargs):
        nonlocal response_idx
        res = responses[response_idx]
        msg = res.choices[0].message
        msg.model_dump.return_value = {
            "tool_calls": msg.tool_calls,
            "content": msg.content
        }
        response_idx = min(response_idx + 1, len(responses) - 1)
        return res

    with patch("squad_os.agents.base.litellm.acompletion", side_effect=mock_acompletion):
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
        project_path = agent.active_branch.project_path

    file_path = os.path.join(project_path, "hello_async.txt")
    assert os.path.exists(file_path), f"Expected file {file_path} to exist after agent execution."

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert content == "Hello SquadOS"
