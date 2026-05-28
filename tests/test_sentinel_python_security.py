import pytest
from squad_os.tools.registry import _validate_python_code

class TestSentinelPythonSecurity:
    """Tests for Sentinel's AST-based Python code validation."""

    @pytest.mark.parametrize("code,expected_msg", [
        ("os.system('ls')", "Blocked: dangerous call 'os.system'"),
        ("os. system('ls')", "Blocked: dangerous call 'os.system'"),
        ("getattr(os, 'system')", "Blocked: use of forbidden built-in 'getattr'"),
        ("os.__getattribute__('system')", "Blocked: access to sensitive attribute '__getattribute__'"),
        ("__import__('os')", "Blocked: use of forbidden built-in '__import__'"),
        ("eval('1+1')", "Blocked: use of forbidden built-in 'eval'"),
        ("exec('print(1)')", "Blocked: use of forbidden built-in 'exec'"),
        ("compile('1+1', '', 'eval')", "Blocked: use of forbidden built-in 'compile'"),
        ("import subprocess; subprocess.run(['ls'])", "Blocked: dangerous call 'subprocess.run'"),
        ("shutil.rmtree('/')", "Blocked: dangerous call 'shutil.rmtree'"),
        ("shutil. rmtree('/')", "Blocked: dangerous call 'shutil.rmtree'"),
        ("import os as o; o.system('ls')", "Blocked: dangerous call 'os.system'"),
        ("from os import system; system('ls')", "Blocked: dangerous call 'os.system' (imported as system)"),
        ("from subprocess import run as r; r(['ls'])", "Blocked: dangerous call 'subprocess.run' (imported as r)"),
        ("import subprocess as sp; sp.Popen(['ls'])", "Blocked: dangerous call 'subprocess.Popen'"),
    ])
    def test_blocked_dangerous_code(self, code, expected_msg):
        valid, msg = _validate_python_code(code)
        assert not valid
        assert expected_msg in msg

    @pytest.mark.parametrize("code", [
        "print('hello world')",
        "x = [1, 2, 3]\nprint(sum(x))",
        "def add(a, b):\n    return a + b\nprint(add(5, 10))",
        "import math\nprint(math.sqrt(16))",
        "class MyClass:\n    def __init__(self, val):\n        self.val = val\nobj = MyClass(10)\nprint(obj.val)",
    ])
    def test_allowed_safe_code(self, code):
        valid, msg = _validate_python_code(code)
        assert valid, f"Expected safe code to be allowed, but got: {msg}"

    def test_empty_code(self):
        valid, msg = _validate_python_code("")
        assert not valid
        assert "Empty code not allowed" in msg

    def test_syntax_error(self):
        valid, msg = _validate_python_code("if True print('hi')")
        assert not valid
        assert "Syntax error in code" in msg
