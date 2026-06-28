
import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add the current directory to sys.path so we can import squad_os
sys.path.append(os.getcwd())

from squad_os.tools.desktop import DesktopControlTool

class TestDesktopControlSecurity(unittest.TestCase):
    def setUp(self):
        self.tool = DesktopControlTool()

    @patch('platform.system')
    @patch('subprocess.Popen')
    def test_open_app_windows_secure(self, mock_popen, mock_system):
        # Simulate Windows environment
        mock_system.return_value = 'Windows'

        # Test case 1: Malicious input
        malicious_app = 'calc.exe & echo pwned'
        self.tool._get_backend().open_app(malicious_app)

        # Verify that subprocess.Popen was called with shell=False and split arguments
        # 'calc.exe & echo pwned' in non-posix shlex split becomes ['calc.exe', '&', 'echo', 'pwned']
        mock_popen.assert_called_with(['calc.exe', '&', 'echo', 'pwned'], shell=False)

        # Test case 2: Path with spaces
        path_with_spaces = '"C:\\Program Files\\App\\app.exe" --arg'
        self.tool._get_backend().open_app(path_with_spaces)
        mock_popen.assert_called_with(['C:\\Program Files\\App\\app.exe', '--arg'], shell=False)

    @patch('platform.system')
    @patch('subprocess.Popen')
    def test_open_app_darwin_secure(self, mock_popen, mock_system):
        # Simulate macOS environment
        mock_system.return_value = 'Darwin'

        # Test argument injection prevention
        app_with_args = '--args malicious'
        self.tool._get_backend().open_app(app_with_args)

        # Verify that it uses -- to prevent argument injection
        mock_popen.assert_called_with(['open', '--', '--args malicious'])

    @patch('platform.system')
    @patch('subprocess.Popen')
    def test_open_app_linux_secure(self, mock_popen, mock_system):
        # Simulate Linux environment
        mock_system.return_value = 'Linux'

        # Test basic execution
        app = 'firefox'
        self.tool._get_backend().open_app(app)

        # Verify that it calls xdg-open without -- as it's not universally supported
        mock_popen.assert_called_with(['xdg-open', 'firefox'])

if __name__ == '__main__':
    unittest.main()
