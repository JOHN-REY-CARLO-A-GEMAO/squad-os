import pytest
import os
import asyncio
from squad_os.tools.registry import TerminalTool

@pytest.mark.asyncio
async def test_terminal_tool_security():
    workspace = os.path.realpath("workspace/projects/test_terminal_security")
    os.makedirs(workspace, exist_ok=True)

    # Create a secret file outside
    secret_path = os.path.realpath("secret_terminal_test.txt")
    with open(secret_path, "w") as f:
        f.write("SECRET_STUFF")

    tool = TerminalTool(branch_id="test_terminal_security")

    # Test path traversal in various ways
    traversal_commands = [
        "ls ../../..",
        f"cat {secret_path}",
        "ls /etc",
        "cat ../../../secret_terminal_test.txt"
    ]

    for cmd in traversal_commands:
        result = await tool.execute(cmd)
        assert "SECURITY_ERROR" in result or "Access denied" in result or "Path traversal detected" in result

    # Test safe command
    safe_result = await tool.execute("ls .")
    assert "SECURITY_ERROR" not in safe_result

    # Cleanup
    if os.path.exists(secret_path):
        os.remove(secret_path)
