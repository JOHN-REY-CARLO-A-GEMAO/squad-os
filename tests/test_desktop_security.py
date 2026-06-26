import sys
from unittest.mock import MagicMock, patch
import pytest
import asyncio

# Mock missing dependencies that are imported via squad_os.tools
sys.modules['duckduckgo_search'] = MagicMock()
sys.modules['ddgs'] = MagicMock()
sys.modules['pywinauto'] = MagicMock()
sys.modules['pywinauto.desktop'] = MagicMock()
sys.modules['pyautogui'] = MagicMock()
sys.modules['pyperclip'] = MagicMock()
sys.modules['mss'] = MagicMock()
sys.modules['pytesseract'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()
sys.modules['Cocoa'] = MagicMock()
sys.modules['Foundation'] = MagicMock()
sys.modules['ApplicationServices'] = MagicMock()
sys.modules['dbus'] = MagicMock()
sys.modules['ffmpeg'] = MagicMock()
sys.modules['playwright'] = MagicMock()
sys.modules['playwright.async_api'] = MagicMock()
sys.modules['litellm'] = MagicMock()

from squad_os.tools.desktop import DesktopControlTool

@pytest.mark.asyncio
async def test_open_app_windows_security():
    """Verify that open_app on Windows uses shell=False and safe splitting."""
    with patch("platform.system", return_value="Windows"):
        tool = DesktopControlTool()
        # We need to trigger backend initialization which uses platform.system()
        # The backend is lazily initialized.

        with patch("subprocess.Popen") as mock_popen:
            # Test simple app
            await tool.execute(action="open_app", app="calc.exe")
            mock_popen.assert_called_with(["calc.exe"], shell=False)

            # Test app with arguments
            await tool.execute(action="open_app", app="notepad.exe 'my file.txt'")
            # In Windows mode (posix=False), shlex keeps the quotes
            mock_popen.assert_called_with(["notepad.exe", "'my file.txt'"], shell=False)

            # Test attempt at command injection
            await tool.execute(action="open_app", app="calc.exe & echo evil")
            # shlex.split(..., posix=False) will keep the & as part of the arguments or separate tokens
            # but because shell=False, it won't be interpreted by a shell.
            # In Windows non-posix mode:
            # shlex.split("calc.exe & echo evil", posix=False) -> ['calc.exe', '&', 'echo', 'evil']
            mock_popen.assert_called_with(["calc.exe", "&", "echo", "evil"], shell=False)

@pytest.mark.asyncio
async def test_open_app_unix_security():
    """Verify that open_app on non-Windows platforms (e.g., Darwin) still uses list-based Popen."""
    with patch("platform.system", return_value="Darwin"):
        tool = DesktopControlTool()

        with patch("subprocess.Popen") as mock_popen:
            await tool.execute(action="open_app", app="Calculator")
            mock_popen.assert_called_with(["open", "Calculator"])
            # shell defaults to False in Popen
