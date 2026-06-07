import pytest
from squad_os.tools.registry import _validate_python_code

def test_validate_python_code_simple_safe():
    code = "print('Hello, World!')"
    valid, msg = _validate_python_code(code)
    assert valid is True
    assert msg == ""

def test_validate_python_code_direct_danger():
    code = "import os; os.system('ls')"
    valid, msg = _validate_python_code(code)
    assert valid is False
    assert "os.system" in msg or "system" in msg

def test_validate_python_code_alias_bypass():
    code = "import os as o; o.system('ls')"
    valid, msg = _validate_python_code(code)
    # This is currently True with regex, should be False after fix
    assert valid is False, f"Should block aliased os.system, but got valid={valid}"

def test_validate_python_code_getattr_bypass():
    code = "import os; getattr(os, 'sys' + 'tem')('ls')"
    valid, msg = _validate_python_code(code)
    # This is currently True with regex, should be False after fix
    assert valid is False, f"Should block getattr(os, 'system'), but got valid={valid}"

def test_validate_python_code_eval_assignment_bypass():
    code = "e = eval; e('print(1)')"
    valid, msg = _validate_python_code(code)
    # This is currently True with regex, should be False after fix
    assert valid is False, f"Should block eval via assignment, but got valid={valid}"

def test_validate_python_code_dynamic_import_bypass():
    code = "__import__('o' + 's').system('ls')"
    valid, msg = _validate_python_code(code)
    # This is currently True with regex, should be False after fix
    assert valid is False, f"Should block dynamic import bypass, but got valid={valid}"

def test_validate_python_code_from_import_danger():
    code = "from os import system; system('ls')"
    valid, msg = _validate_python_code(code)
    assert valid is False
    assert "system" in msg

def test_validate_python_code_internal_attribute_access():
    code = "().__class__.__base__.__subclasses__()[0]"
    valid, msg = _validate_python_code(code)
    assert valid is False
    assert "attribute" in msg or "forbidden" in msg.lower()
