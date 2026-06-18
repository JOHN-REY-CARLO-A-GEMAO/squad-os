import pytest
from unittest.mock import MagicMock, patch
from squad_os.tools.desktop import DesktopControlTool
from squad_os.tools.registry import _validate_python_code

class TestDesktopSecurity:
    @patch("subprocess.Popen")
    @patch("platform.system")
    def test_open_app_shell_false_windows(self, mock_system, mock_popen):
        mock_system.return_value = "Windows"
        tool = DesktopControlTool()
        # We need to trigger backend initialization or mock it
        # Since _get_backend is lazy, we can just call open_app
        tool._get_backend().open_app("calc.exe")

        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args
        assert kwargs.get("shell") is False
        assert args[0] == "calc.exe"

class TestPythonSandboxSecurity:
    def test_block_eval(self):
        code = "eval('print(1)')"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "forbidden built-in" in msg

    def test_block_exec(self):
        code = "exec('import os')"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "forbidden built-in" in msg

    def test_block_os_system(self):
        code = "import os\nos.system('ls')"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "forbidden module" in msg or "forbidden module attribute" in msg

    def test_block_getattr_obfuscation(self):
        code = "getattr(__builtins__, 'eval')('print(1)')"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "forbidden built-in" in msg

    def test_block_subclasses_escape(self):
        code = "().__class__.__base__.__subclasses__()"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "dunder attribute" in msg

    def test_block_aliased_import(self):
        code = "import os as o\no.system('ls')"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "forbidden module" in msg or "forbidden module attribute" in msg

    def test_allow_safe_code(self):
        code = "x = 1 + 1\nprint(x)"
        valid, msg = _validate_python_code(code)
        assert valid, f"Expected safe code to be valid, but got: {msg}"

    def test_block_import_from(self):
        code = "from os import system\nsystem('ls')"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "forbidden module" in msg

    def test_block_globals_access(self):
        code = "globals()['__builtins__']"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "forbidden built-in" in msg
