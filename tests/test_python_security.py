import pytest
from squad_os.tools.registry import _validate_python_code

def test_simple_safe_code():
    code = "print('Hello, world!')"
    valid, msg = _validate_python_code(code)
    assert valid
    assert msg == ""

def test_blocked_os_import():
    code = "import os"
    valid, msg = _validate_python_code(code)
    assert not valid
    assert "Import of dangerous module 'os'" in msg

def test_blocked_os_alias_system():
    code = """
import os as o
o.system('ls')
"""
    valid, msg = _validate_python_code(code)
    assert not valid
    assert "Call to dangerous method 'os.system()'" in msg

def test_blocked_subprocess_run():
    code = "import subprocess; subprocess.run(['ls'])"
    valid, msg = _validate_python_code(code)
    assert not valid
    assert "dangerous" in msg.lower()

def test_blocked_from_os_import_system():
    code = "from os import system; system('ls')"
    valid, msg = _validate_python_code(code)
    assert not valid
    assert "Import from dangerous module 'os'" in msg

def test_blocked_eval():
    code = "eval('1 + 1')"
    valid, msg = _validate_python_code(code)
    assert not valid
    assert "Call to forbidden builtin 'eval()'" in msg

def test_blocked_getattr_dynamic():
    code = "getattr(os, 'sys' + 'tem')('ls')"
    valid, msg = _validate_python_code(code)
    assert not valid
    assert "getattr() with non-literal attribute name is forbidden" in msg

def test_blocked_getattr_dangerous_method():
    code = "getattr(os, 'system')('ls')"
    valid, msg = _validate_python_code(code)
    assert not valid
    assert "Dynamic access to dangerous attribute/method 'system' via getattr" in msg

def test_blocked_sensitive_attribute():
    code = "[].__class__.__subclasses__()"
    valid, msg = _validate_python_code(code)
    assert not valid
    assert "Access to sensitive attribute '__subclasses__'" in msg

def test_syntax_error():
    code = "if True print('oops')"
    valid, msg = _validate_python_code(code)
    assert not valid
    assert "Syntax error" in msg

def test_empty_code():
    valid, msg = _validate_python_code("")
    assert not valid
    assert "Empty code" in msg
