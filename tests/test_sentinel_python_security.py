import pytest
from squad_os.tools.registry import _validate_python_code

class TestSentinelPythonSecurity:
    """Tests for Sentinel's AST-based Python validation."""

    def test_allow_safe_code(self):
        code = "print('Hello, World!'); x = 1 + 2; print(x)"
        valid, msg = _validate_python_code(code)
        assert valid, f"Expected safe code to be allowed, got: {msg}"

    def test_block_forbidden_builtin_eval(self):
        code = "eval('print(123)')"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "forbidden built-in 'eval'" in msg

    def test_block_forbidden_builtin_exec(self):
        code = "exec('import os')"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "forbidden built-in 'exec'" in msg

    def test_block_dangerous_method_os_system(self):
        code = "import os; os.system('ls')"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "dangerous method 'os.system'" in msg

    def test_block_dangerous_method_alias(self):
        code = "import os as o; o.system('ls')"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "dangerous method 'os.system'" in msg

    def test_block_dangerous_method_direct_import(self):
        code = "from os import system; system('ls')"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "Direct import of dangerous method 'os.system'" in msg

    def test_block_dangerous_method_direct_import_alias(self):
        code = "from os import system as s; s('ls')"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "Direct import of dangerous method 'os.system'" in msg

    def test_block_sensitive_attribute_globals(self):
        code = "print(x.__globals__)"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "sensitive attribute '__globals__'" in msg

    def test_block_sensitive_attribute_subclasses(self):
        code = "obj.__subclasses__()"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "sensitive attribute '__subclasses__'" in msg

    def test_block_getattr_sensitive(self):
        code = "getattr(obj, '__globals__')"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "sensitive attribute '__globals__'" in msg

    def test_block_getattr_dangerous_method(self):
        code = "import os; getattr(os, 'system')('ls')"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "dangerous method 'os.system'" in msg

    def test_block_getattr_non_literal(self):
        code = "x = '__globals__'; getattr(obj, x)"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "must use literal string for attribute name" in msg

    def test_block_obfuscated_attribute_access(self):
        # This would pass regex but should be caught by AST if we check all Attributes
        code = "func = lambda: None; print(func.__code__)"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "sensitive attribute '__code__'" in msg

    def test_block_subprocess_run(self):
        code = "import subprocess; subprocess.run(['ls'])"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "dangerous method 'subprocess.run'" in msg

    def test_block_shutil_rmtree(self):
        code = "import shutil; shutil.rmtree('/')"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "dangerous method 'shutil.rmtree'" in msg

    def test_syntax_error_handling(self):
        code = "if True:" # Missing indentation/body
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "Python syntax error" in msg
