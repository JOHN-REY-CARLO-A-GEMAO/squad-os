import pytest
import os
import asyncio
from squad_os.tools.registry import TerminalTool

@pytest.mark.asyncio
async def test_terminal_redirection_traversal():
    branch_id = "test_redir_security"
    workspace = os.path.realpath(os.path.join("workspace", "projects", branch_id))
    os.makedirs(workspace, exist_ok=True)

    tool = TerminalTool(branch_id=branch_id)

    # Attempt redirection to /tmp which is outside workspace
    command = "ls > /tmp/traversal_output"
    result = await tool.execute(command)

    assert "SECURITY_ERROR" in result
    assert "Access denied" in result
    assert "/tmp/traversal_output" in result

    # Verify file was NOT created
    assert not os.path.exists("/tmp/traversal_output")

@pytest.mark.asyncio
async def test_terminal_chained_command_traversal():
    branch_id = "test_chained_security"
    workspace = os.path.realpath(os.path.join("workspace", "projects", branch_id))
    os.makedirs(workspace, exist_ok=True)

    tool = TerminalTool(branch_id=branch_id)

    # Chained command with traversal
    command = "ls && cat ../../../secret.txt"
    result = await tool.execute(command)

    assert "SECURITY_ERROR" in result
    assert "../../../secret.txt" in result

@pytest.mark.asyncio
async def test_terminal_allowed_command_only():
    branch_id = "test_allowed_only"
    workspace = os.path.realpath(os.path.join("workspace", "projects", branch_id))
    os.makedirs(workspace, exist_ok=True)

    tool = TerminalTool(branch_id=branch_id)

    # Try an unauthorized command even if path is safe
    command = "apt-get update"
    result = await tool.execute(command)

    assert "SECURITY_ERROR" in result
    assert "apt-get" in result

@pytest.mark.asyncio
async def test_terminal_absolute_allowed_command():
    branch_id = "test_abs_allowed"
    workspace = os.path.realpath(os.path.join("workspace", "projects", branch_id))
    os.makedirs(workspace, exist_ok=True)

    tool = TerminalTool(branch_id=branch_id)

    # Absolute path to an allowed command (ls) should be permitted
    # assuming /bin/ls exists (common on Linux)
    if os.path.exists("/bin/ls"):
        command = "/bin/ls"
        result = await tool.execute(command)
        assert "SECURITY_ERROR" not in result
        assert "STDOUT" in result
