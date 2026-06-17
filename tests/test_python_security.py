import pytest
from squad_os.tools.registry import _validate_python_code

def test_getattr_bypass():
    code = """
import os
m = "sys" + "tem"
getattr(os, m)("ls")
"""
    is_valid, msg = _validate_python_code(code)
    assert not is_valid
    assert "Forbidden built-in call: getattr" in msg

def test_alias_bypass():
    code = """
import os as o
o.system("ls")
"""
    is_valid, msg = _validate_python_code(code)
    assert not is_valid
    assert "Forbidden access to 'system' on module 'o'" in msg

def test_subclasses_bypass():
    code = "[].__class__.__base__.__subclasses__()"
    is_valid, msg = _validate_python_code(code)
    assert not is_valid
    assert "Forbidden internal attribute access: __subclasses__" in msg

def test_complex_eval_bypass():
    code = "(eval)('print(1)')"
    is_valid, msg = _validate_python_code(code)
    assert not is_valid
    assert "Forbidden built-in call: eval" in msg

def test_container_eval_bypass():
    code = "[eval][0]('print(1)')"
    is_valid, msg = _validate_python_code(code)
    assert not is_valid
    assert "Forbidden built-in call: expression" in msg

def test_safe_code():
    code = """
def run_task(task):
    print(f"Running {task}")
run_task("cleanup")
"""
    is_valid, msg = _validate_python_code(code)
    assert is_valid

def test_safe_attribute_access():
    code = """
class MyObj:
    def run(self):
        return "running"
o = MyObj()
o.run()
"""
    is_valid, msg = _validate_python_code(code)
    assert is_valid

def test_forbidden_import_from():
    code = "from os import system"
    is_valid, msg = _validate_python_code(code)
    assert not is_valid
    assert "Forbidden import from: os" in msg
