import os
import json
from unittest.mock import AsyncMock, patch

import pytest
from litellm import ModelResponse
from litellm.types.utils import Message, Choices
from squad_os.agents.base import BaseAgent
from squad_os.tools.registry import FileWriterTool
from squad_os.database.session import init_db


def make_tool_call_response(tool_name: str, args: dict):
    msg = Message(
        content=None,
        tool_calls=[{
            "id": "call_1",
            "function": {"name": tool_name, "arguments": json.dumps(args)},
            "type": "function",
        }]
    )
    return ModelResponse(
        id="test",
        choices=[Choices(finish_reason="tool_calls", index=0, message=msg)],
        usage={"prompt_tokens": 10, "completion_tokens": 5}
    )


def make_text_response(text: str):
    msg = Message(content=text)
    return ModelResponse(
        id="test",
        choices=[Choices(finish_reason="stop", index=0, message=msg)],
        usage={"prompt_tokens": 10, "completion_tokens": 5}
    )


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

    mock = AsyncMock(side_effect=[
        make_tool_call_response("write_file", {"filename": "hello_async.txt", "content": "Hello SquadOS"}),
        make_text_response("File written successfully."),
    ])

    with patch("litellm.acompletion", mock):
        result = await agent.execute_task(
            "Write 'Hello SquadOS' to a file named 'hello_async.txt' in the workspace.",
            context=""
        )

    assert result is not None

    branch_path = agent.active_branch.project_path if agent.active_branch else "workspace"
    file_path = os.path.join(branch_path, "hello_async.txt")
    assert os.path.exists(file_path), f"Expected file {file_path} to exist after agent execution."

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert content == "Hello SquadOS"
