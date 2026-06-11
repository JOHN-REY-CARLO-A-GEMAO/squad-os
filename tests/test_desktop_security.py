import pytest
from unittest.mock import patch, MagicMock
from squad_os.tools.desktop import DesktopControlTool

@pytest.mark.asyncio
async def test_open_app_windows_security():
    """Verify that open_app on Windows does NOT use shell=True."""
    # Mock platform.system to return 'Windows' BEFORE instantiating the tool
    with patch("platform.system", return_value="Windows"):
        tool = DesktopControlTool()

        # Mock subprocess.Popen
        with patch("subprocess.Popen") as mock_popen:
            # Execute the action
            # 'app' contains a potential injection attempt
            await tool.execute(action="open_app", app="calc.exe & echo pwned")

            # Check how Popen was called
            mock_popen.assert_called_once()
            args, kwargs = mock_popen.call_args

            # On Windows, it should be called with the string directly
            assert args[0] == "calc.exe & echo pwned"

            # IMPORTANT: shell should either be False (default) or not present in kwargs
            # If it IS present, it MUST NOT be True.
            assert kwargs.get("shell") is not True

@pytest.mark.asyncio
async def test_open_app_linux_security():
    """Verify that open_app on Linux uses a list and NOT shell=True."""
    with patch("platform.system", return_value="Linux"):
        tool = DesktopControlTool()
        with patch("subprocess.Popen") as mock_popen:
            await tool.execute(action="open_app", app="ls; echo pwned")

            mock_popen.assert_called_once()
            args, kwargs = mock_popen.call_args

            # On Linux, it should use xdg-open in a list
            assert args[0] == ["xdg-open", "ls; echo pwned"]
            assert kwargs.get("shell") is not True

@pytest.mark.asyncio
async def test_open_app_darwin_security():
    """Verify that open_app on macOS uses a list and NOT shell=True."""
    with patch("platform.system", return_value="Darwin"):
        tool = DesktopControlTool()
        with patch("subprocess.Popen") as mock_popen:
            await tool.execute(action="open_app", app="ls; echo pwned")

            mock_popen.assert_called_once()
            args, kwargs = mock_popen.call_args

            # On Darwin, it should use open in a list
            assert args[0] == ["open", "ls; echo pwned"]
            assert kwargs.get("shell") is not True
