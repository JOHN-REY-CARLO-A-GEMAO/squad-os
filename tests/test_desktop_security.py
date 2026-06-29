import asyncio
import subprocess
import platform
import shlex
from unittest.mock import MagicMock, patch
import sys
import os

# Mock all dependencies that might be imported by squad_os.tools.desktop
mock_modules = [
    'pyautogui', 'pyperclip', 'mss', 'pytesseract', 'PIL',
    'duckduckgo_search', 'ddgs', 'pywinauto', 'pyobjc', 'Cocoa', 'Foundation',
    'ApplicationServices', 'dbus', 'squad_os.database.session',
    'ffmpeg', 'playwright', 'playwright.async_api', 'litellm', 'pydantic',
    'pydantic_settings', 'yaml', 'yaml_include'
]
for mod in mock_modules:
    sys.modules[mod] = MagicMock()

# Manually mock DDGS if it's imported via from ... import
class MockDDGS:
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def text(self, *args, **kwargs): return []

sys.modules['duckduckgo_search'].DDGS = MockDDGS

from squad_os.tools.desktop import DesktopControlTool

async def test_open_app_windows_security():
    """Verify that Windows open_app does NOT use shell=True and uses token list."""
    tool = DesktopControlTool()
    with patch('subprocess.Popen') as mock_popen:
        with patch('platform.system', return_value='Windows'):
            # We want to ensure it handles spaces and avoids shell injection
            # app path with spaces and arguments
            await tool.execute(action="open_app", app='"C:\\Program Files\\app.exe" --arg')

            args, kwargs = mock_popen.call_args
            assert kwargs.get('shell') is False, "Windows open_app must use shell=False"
            assert isinstance(args[0], list), "Windows open_app must pass arguments as a list"
            # It should have split the command correctly and stripped quotes
            assert args[0] == ["C:\\Program Files\\app.exe", "--arg"]

async def test_open_app_linux_security():
    """Verify that Linux open_app uses -- separator to prevent argument injection."""
    tool = DesktopControlTool()
    with patch('subprocess.Popen') as mock_popen:
        with patch('platform.system', return_value='Linux'):
            await tool.execute(action="open_app", app="--version")

            args, kwargs = mock_popen.call_args
            # Expected: ["xdg-open", "--", "--version"]
            assert args[0] == ["xdg-open", "--", "--version"], "Linux open_app must use -- separator"

async def test_open_app_darwin_security():
    """Verify that macOS open_app uses -- separator to prevent argument injection."""
    tool = DesktopControlTool()
    with patch('subprocess.Popen') as mock_popen:
        with patch('platform.system', return_value='Darwin'):
            await tool.execute(action="open_app", app="--version")

            args, kwargs = mock_popen.call_args
            # Expected: ["open", "--", "--version"]
            assert args[0] == ["open", "--", "--version"], "macOS open_app must use -- separator"

async def run_all_security_tests():
    print("Running DesktopControlTool security verification tests...")
    try:
        await test_open_app_windows_security()
        await test_open_app_linux_security()
        await test_open_app_darwin_security()
        print("\nAll security tests passed successfully!")
    except Exception as e:
        print(f"\nSecurity tests failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_all_security_tests())
