import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import shlex
import asyncio

# Mock environment dependencies
for mod in ['duckduckgo_search', 'pyautogui', 'pywinauto', 'mss', 'pytesseract', 'PIL', 'ffmpeg', 'playwright', 'playwright.async_api', 'litellm']:
    sys.modules[mod] = MagicMock()

sys.path.append(os.getcwd())
from squad_os.tools.desktop import DesktopControlTool

class TestDesktopSecurity(unittest.TestCase):
    def setUp(self):
        self.tool = DesktopControlTool()

    @patch('platform.system')
    @patch('subprocess.Popen')
    def test_open_app_windows_command_injection(self, mock_popen, mock_system):
        """Verify that open_app on Windows prevents command injection by using shell=False."""
        mock_system.return_value = 'Windows'
        malicious_input = "calc.exe & echo pwned"

        asyncio.run(self.tool.execute(action="open_app", app=malicious_input))

        expected_cmd = [t.strip('"') for t in shlex.split(malicious_input, posix=False)]
        mock_popen.assert_called_once_with(expected_cmd, shell=False)

    @patch('platform.system')
    @patch('subprocess.Popen')
    def test_open_app_windows_quoted_path(self, mock_popen, mock_system):
        """Verify that open_app on Windows handles quoted paths correctly without double-quoting."""
        mock_system.return_value = 'Windows'
        quoted_path = '"C:\\Program Files\\App.exe" --arg "val with space"'

        asyncio.run(self.tool.execute(action="open_app", app=quoted_path))

        # Expected: quotes stripped from tokens
        expected_cmd = ['C:\\Program Files\\App.exe', '--arg', 'val with space']
        mock_popen.assert_called_once_with(expected_cmd, shell=False)

    @patch('platform.system')
    @patch('subprocess.Popen')
    def test_open_app_darwin_argument_injection(self, mock_popen, mock_system):
        """Verify that open_app on macOS prevents argument injection using -- separator."""
        mock_system.return_value = 'Darwin'
        app_name = "-a Calculator" # Attempting to inject flags

        asyncio.run(self.tool.execute(action="open_app", app=app_name))

        mock_popen.assert_called_once_with(["open", "--", app_name])

    @patch('platform.system')
    @patch('subprocess.Popen')
    def test_open_app_linux_argument_injection(self, mock_popen, mock_system):
        """Verify that open_app on Linux prevents argument injection using -- separator."""
        mock_system.return_value = 'Linux'
        app_name = "--help"

        asyncio.run(self.tool.execute(action="open_app", app=app_name))

        mock_popen.assert_called_once_with(["xdg-open", "--", app_name])

if __name__ == "__main__":
    unittest.main()
