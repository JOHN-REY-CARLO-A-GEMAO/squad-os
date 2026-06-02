
import pytest
from squad_os.tools.registry import _validate_python_code

class TestPythonSecurityAST:
    """Tests for Sentinel's AST-based Python code validation."""

    def test_block_direct_import(self):
        valid, msg = _validate_python_code("import os")
        assert not valid
        assert "dangerous module" in msg

    def test_block_import_alias(self):
        valid, msg = _validate_python_code("import os as o")
        assert not valid
        assert "dangerous module" in msg

    def test_block_import_from(self):
        valid, msg = _validate_python_code("from os import system")
        assert not valid
        assert "dangerous module" in msg

    def test_block_dangerous_builtin(self):
        valid, msg = _validate_python_code("eval('1+1')")
        assert not valid
        assert "forbidden function" in msg

    def test_block_dangerous_method_call(self):
        valid, msg = _validate_python_code("os.system('ls')")
        # Even if os wasn't blocked on import, system() should be blocked
        assert not valid
        assert "forbidden function" in msg

    def test_block_aliased_method_call(self):
        # This checks if we block the method name even if the module is aliased
        # (Assuming the attacker somehow bypassed the import check, e.g. it was already in namespace)
        valid, msg = _validate_python_code("o.system('ls')")
        assert not valid
        assert "forbidden function" in msg

    def test_block_getattr_bypass(self):
        valid, msg = _validate_python_code("import os; getattr(os, 'system')('ls')")
        assert not valid
        # It should be blocked by 'os' import, but let's test getattr specifically
        valid, msg = _validate_python_code("getattr(some_obj, 'system')")
        assert not valid
        assert "dynamic access" in msg

    def test_block_sensitive_attributes(self):
        valid, msg = _validate_python_code("().__class__.__base__.__subclasses__()")
        assert not valid
        assert "sensitive attribute" in msg

    def test_allow_safe_code(self):
        code = """
def greet(name):
    return f"Hello, {name}"

print(greet("World"))
"""
        valid, msg = _validate_python_code(code)
        assert valid, f"Expected safe code to be allowed, got: {msg}"

    def test_block_open(self):
        valid, msg = _validate_python_code("open('/etc/passwd', 'r')")
        assert not valid
        assert "forbidden function" in msg

    def test_block_importlib(self):
        valid, msg = _validate_python_code("import importlib; importlib.import_module('os')")
        assert not valid
        assert "dangerous module" in msg

    def test_syntax_error(self):
        valid, msg = _validate_python_code("if True print('hi')")
        assert not valid
        assert "Syntax error" in msg
