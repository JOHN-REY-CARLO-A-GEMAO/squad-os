import pytest
from squad_os.tools.registry import _validate_python_code

class TestPythonSecurityAST:
    """Tests for the AST-based Python code validation."""

    def test_block_simple_os_system(self):
        code = "import os; os.system('echo hello')"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "Blocked" in msg

    def test_block_obfuscated_import(self):
        # The bypass that regex missed
        code = "__import__('o' + 's').system('echo pwned')"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "forbidden builtin" in msg or "dangerous module" in msg

    def test_block_getattr_bypass(self):
        code = "getattr(__import__('os'), 'system')('echo pwned')"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "forbidden builtin" in msg

    def test_block_aliased_import(self):
        code = "import os as o; o.system('ls')"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "dangerous method" in msg

    def test_block_from_import(self):
        code = "from os import system; system('ls')"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "dangerous method" in msg

    def test_block_dunder_access(self):
        code = "x = [].__class__.__base__.__subclasses__()"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "sensitive attribute" in msg

    def test_allow_safe_code(self):
        code = "x = 1 + 2; print(f'Result: {x}')"
        valid, msg = _validate_python_code(code)
        assert valid, f"Expected safe code to be allowed, got: {msg}"

    def test_block_subprocess_popen(self):
        code = "import subprocess; subprocess.Popen(['ls'])"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "dangerous module" in msg or "dangerous method" in msg

    def test_syntax_error_handling(self):
        code = "if x = 5: pass"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "Syntax error" in msg
