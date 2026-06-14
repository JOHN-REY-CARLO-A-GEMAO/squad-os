import pytest
import asyncio
from unittest.mock import MagicMock, patch
from squad_os.tools.desktop import DesktopControlTool

@pytest.mark.asyncio
async def test_open_app_security():
    # Mock platform to windows
    with patch('platform.system', return_value='Windows'):
        with patch('subprocess.Popen') as mock_popen:
            tool = DesktopControlTool()

            # Test a normal app name
            await tool.execute(action="open_app", app="calc.exe")
            mock_popen.assert_called_with("calc.exe", shell=False)

            # Test an injection attempt
            await tool.execute(action="open_app", app="calc.exe & echo evil")
            mock_popen.assert_called_with("calc.exe & echo evil", shell=False)
