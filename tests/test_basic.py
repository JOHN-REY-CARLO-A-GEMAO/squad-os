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

    # Mocking as async
    async def async_side_effect(*args, **kwargs):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Done.", tool_calls=None))]
        mock_response.usage.prompt_tokens = 5
        mock_response.usage.completion_tokens = 5
        return mock_response

    with patch("litellm.acompletion", side_effect=async_side_effect):
        result = await agent.execute_task("Test task", context="")
    assert result is not None

