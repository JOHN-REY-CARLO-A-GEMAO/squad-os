import unittest
from unittest.mock import MagicMock, patch
import os
import ast
import asyncio
from squad_os.tools.desktop import DesktopControlTool
from squad_os.tools.registry import _validate_python_code

class TestSentinelFixes(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    @patch('subprocess.Popen')
    @patch('platform.system')
    def test_open_app_windows_no_shell(self, mock_system, mock_popen):
        mock_system.return_value = 'Windows'
        tool = DesktopControlTool()

        # Test basic app opening
        self.loop.run_until_complete(tool._open_app("notepad.exe"))
        mock_popen.assert_called_with("notepad.exe", shell=False)

        # Test that shell=True is NOT used even with suspicious strings
        self.loop.run_until_complete(tool._open_app("calc.exe & echo vulnerable"))
        mock_popen.assert_called_with("calc.exe & echo vulnerable", shell=False)

    def test_python_validation_bypasses(self):
        # These should all be BLOCKED now
        bypasses = [
            "import os as o; o.system('ls')",
            "import subprocess as sp; sp.run(['ls'])",
            "c = eval; c('ls')",
            "getattr(os, 'system')",
            "o = os; o.system('ls')",
            "from os import system as s; s('ls')",
            "import importlib; importlib.import_module('os').system('ls')"
        ]

        for code in bypasses:
            valid, msg = _validate_python_code(code)
            self.assertFalse(valid, f"Should have blocked: {code}. Message: {msg}")

    def test_python_validation_legit(self):
        # These should be ALLOWED
        legit = [
            "print('Hello World')",
            "import json; json.dumps({'a': 1})",
            "import math; math.sqrt(16)",
            "x = [i for i in range(10)]",
        ]

        for code in legit:
            valid, msg = _validate_python_code(code)
            self.assertTrue(valid, f"Should have allowed: {code}. Error: {msg}")

if __name__ == '__main__':
    unittest.main()
