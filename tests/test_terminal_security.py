import asyncio
import os
import shutil
import pytest
from squad_os.tools.registry import TerminalTool

@pytest.mark.asyncio
async def test_terminal_security_comprehensive():
    workspace = os.path.realpath("workspace/test_terminal_security")
    if os.path.exists(workspace):
        shutil.rmtree(workspace)
    os.makedirs(workspace, exist_ok=True)

    # Secret outside workspace
    secret_path = os.path.realpath("outside_secret.txt")
    with open(secret_path, "w") as f:
        f.write("SECRET_DATA")

    try:
        tool = TerminalTool()
        tool.workspace = workspace # Override for test

        # 1. Path traversal in cat
        res = await tool.execute(f"cat {secret_path}")
        assert "SECURITY_ERROR" in res
        assert "Access denied" in res

        # 2. Path traversal with relative path
        res = await tool.execute("cat ../../outside_secret.txt")
        assert "SECURITY_ERROR" in res

        # 3. Path traversal in redirection
        res = await tool.execute(f"echo hijack > {secret_path}")
        assert "SECURITY_ERROR" in res
        with open(secret_path, "r") as f:
            assert f.read() == "SECRET_DATA" # Ensure it wasn't overwritten

        # 4. Path traversal in piped command
        res = await tool.execute(f"ls | xargs cat > {secret_path}")
        assert "SECURITY_ERROR" in res

        # 5. Shell injection attempt
        res = await tool.execute("ls && cat /etc/passwd")
        assert "SECURITY_ERROR" in res

        # 6. Valid command
        res = await tool.execute("ls -la")
        assert "STDOUT" in res
        assert "SECURITY_ERROR" not in res

        print("Comprehensive terminal security tests PASSED")

    finally:
        if os.path.exists(secret_path):
            os.remove(secret_path)
        if os.path.exists(workspace):
            shutil.rmtree(workspace)

if __name__ == "__main__":
    import sys
    # For running as a script
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_terminal_security_comprehensive())
