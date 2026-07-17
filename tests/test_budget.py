import json
import os
import tempfile
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from litellm import ModelResponse
from litellm.types.utils import Message, Choices

from squad_os.core.budget import TokenBudget
from squad_os.agents.base import BaseAgent
from squad_os.core.projects import ProjectBranch
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
        usage={"prompt_tokens": 50, "completion_tokens": 10}
    )


def make_text_response(text: str):
    msg = Message(content=text)
    return ModelResponse(
        id="test",
        choices=[Choices(finish_reason="stop", index=0, message=msg)],
        usage={"prompt_tokens": 10, "completion_tokens": 5}
    )


class TestTokenBudget:
    def test_default_never_exceeded(self):
        b = TokenBudget()
        assert not b.exceeded
        b.add_usage(100, 50)
        assert not b.exceeded

    def test_add_usage_accumulates(self):
        b = TokenBudget()
        b.add_usage(10, 5)
        b.add_usage(20, 10)
        assert b.prompt_tokens == 30
        assert b.completion_tokens == 15
        assert b.total_tokens == 45

    def test_max_total_tokens(self):
        b = TokenBudget(max_total_tokens=100)
        assert not b.exceeded
        b.add_usage(60, 40)
        assert self._approx(b.total_tokens, 100)
        assert b.exceeded

    def test_max_prompt_tokens(self):
        b = TokenBudget(max_prompt_tokens=50)
        b.add_usage(30, 10)
        assert not b.exceeded
        b.add_usage(20, 5)
        assert b.exceeded

    def test_max_completion_tokens(self):
        b = TokenBudget(max_completion_tokens=20)
        b.add_usage(100, 10)
        assert not b.exceeded
        b.add_usage(100, 10)
        assert b.exceeded

    def test_max_cost_usd(self):
        b = TokenBudget(max_cost_usd=0.05)
        b.add_usage(0, 0, cost_usd=0.03)
        assert not b.exceeded
        b.add_usage(0, 0, cost_usd=0.03)
        assert b.exceeded

    def test_exceeded_returns_false_from_add_usage(self):
        b = TokenBudget(max_total_tokens=50)
        ok = b.add_usage(20, 10)
        assert ok is True
        ok = b.add_usage(20, 10)
        assert ok is False

    def test_snapshot_format(self):
        b = TokenBudget(max_total_tokens=1000)
        b.add_usage(100, 50)
        s = b.snapshot()
        assert s["prompt_tokens"] == 100
        assert s["completion_tokens"] == 50
        assert s["total_tokens"] == 150
        assert "total_cost_usd" in s
        assert "budget_exceeded" in s
        assert s["budget_exceeded"] is False

    def _approx(self, a, b):
        return abs(a - b) < 2  # Allow minor rounding


class TestBudgetInAgent:
    @pytest.mark.asyncio
    async def test_no_budget_runs_normally(self):
        await init_db()
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = BaseAgent(
                role="TestAgent", goal="test", backstory="test",
                tools=[], model_name="gpt-4o-mini"
            )
            branch = ProjectBranch("test-no-budget", base_dir=tmpdir)
            branch.fork()
            agent.active_branch = branch

            mock_response = make_text_response("task done successfully")
            with patch("litellm.acompletion", AsyncMock(return_value=mock_response)):
                result = await agent.execute_task("test task", "context")

            assert result is not None
            assert "error" not in result or result.get("error") is None
            assert "output" in result

    @pytest.mark.asyncio
    async def test_budget_exceeded_returns_early(self):
        await init_db()
        with tempfile.TemporaryDirectory() as tmpdir:
            budget = TokenBudget(max_total_tokens=80)
            writer = FileWriterTool()
            agent = BaseAgent(
                role="TestAgent", goal="test", backstory="test",
                tools=[writer], model_name="gpt-4o-mini",
                token_budget=budget
            )
            branch = ProjectBranch("test-budget-exceeded", base_dir=tmpdir)
            branch.fork()
            agent.active_branch = branch

            tool_response = make_tool_call_response(
                "write_file", {"filename": "out.txt", "content": "data"}
            )
            mock = AsyncMock(return_value=tool_response)
            with patch("litellm.acompletion", mock):
                result = await agent.execute_task("write out.txt", "context")

            assert result.get("error") == "BUDGET_EXCEEDED", (
                f"Expected BUDGET_EXCEEDED error, got: {result}"
            )
            assert result.get("token_budget") is not None
            assert result["token_budget"]["budget_exceeded"] is True
            assert result["token_budget"]["total_tokens"] >= 80

    @pytest.mark.asyncio
    async def test_budget_tokens_in_success_response(self):
        await init_db()
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = BaseAgent(
                role="TestAgent", goal="test", backstory="test",
                tools=[], model_name="gpt-4o-mini"
            )
            branch = ProjectBranch("test-success", base_dir=tmpdir)
            branch.fork()
            agent.active_branch = branch

            mock_response = make_text_response("done")
            with patch("litellm.acompletion", AsyncMock(return_value=mock_response)):
                result = await agent.execute_task("test", "ctx")

            assert result.get("error") is None or result.get("error") != "BUDGET_EXCEEDED"
            tb = result.get("token_budget")
            assert tb is not None, "Success response should include token_budget snapshot"
            assert tb["total_tokens"] > 0
            assert tb["budget_exceeded"] is False
