import pytest
from squad_os.tools.registry import _validate_python_code
from squad_os.store.loader import AgentPackageLoader

def test_validate_python_code_ast():
    # Basic safe code
    valid, msg = _validate_python_code("print('hello')")
    assert valid
    assert msg == ""

    # Dangerous imports
    valid, msg = _validate_python_code("import os")
    assert not valid
    assert "Import of dangerous module 'os'" in msg

    valid, msg = _validate_python_code("import subprocess as sp")
    assert not valid
    assert "Import of dangerous module 'subprocess'" in msg

    # Dangerous methods
    valid, msg = _validate_python_code("import os; os.system('ls')")
    assert not valid
    assert "Use of dangerous method 'os.system()'" in msg

    valid, msg = _validate_python_code("from os import system; system('ls')")
    assert not valid
    assert "Use of dangerous method 'os.system()'" in msg

    # Forbidden built-ins
    valid, msg = _validate_python_code("eval('1+1')")
    assert not valid
    assert "Use of forbidden built-in 'eval()'" in msg

    valid, msg = _validate_python_code("getattr(os, 'system')")
    assert not valid
    assert "Use of forbidden built-in 'getattr()'" in msg

    # Bypasses
    valid, msg = _validate_python_code("my_eval = eval")
    assert not valid
    assert "Access to forbidden built-in 'eval'" in msg

def test_validate_tool_source_ast():
    # Test through PackageLoader
    result = AgentPackageLoader.validate_tool_source("test_tool", "import os; os.system('ls')")
    assert not result.valid
    assert any("Import of dangerous module 'os'" in err for err in result.errors)
    assert any("Use of dangerous method 'os.system()'" in err for err in result.errors)

if __name__ == "__main__":
    # Run tests manually
    test_validate_python_code_ast()
    test_validate_tool_source_ast()
    print("Security tests passed!")
