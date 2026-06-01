import pytest
from squad_os.tools.registry import _validate_python_code

def test_legitimate_code():
    code = """
def hello():
    print('Hello, world!')
    return 1 + 1

x = [i for i in range(10)]
"""
    is_valid, msg = _validate_python_code(code)
    assert is_valid, f"Expected legitimate code to be valid, but got: {msg}"

def test_dangerous_imports():
    bad_codes = [
        "import os",
        "import subprocess",
        "from os import system",
        "import socket",
        "import requests",
        "import pickle",
    ]
    for code in bad_codes:
        is_valid, msg = _validate_python_code(code)
        assert not is_valid, f"Expected '{code}' to be invalid"
        assert "Blocked: import" in msg or "Blocked: dangerous method" in msg or "dangerous module" in msg

def test_forbidden_builtins():
    bad_codes = [
        "eval('1+1')",
        "exec('import os')",
        "compile('x=1', '', 'exec')",
        "__import__('os')",
        "input('Enter something: ')",
    ]
    for code in bad_codes:
        is_valid, msg = _validate_python_code(code)
        assert not is_valid, f"Expected '{code}' to be invalid"
        assert "Blocked: forbidden built-in" in msg

def test_dangerous_methods():
    bad_codes = [
        "import os\nos.system('ls')",
        "import subprocess\nsubprocess.run(['ls'])",
        "import shutil\nshutil.rmtree('/')",
    ]
    # Note: Even if they import it (which is already blocked), the method call should also be blocked.
    for code in bad_codes:
        is_valid, msg = _validate_python_code(code)
        assert not is_valid, f"Expected '{code}' to be invalid"

def test_forbidden_attributes():
    bad_codes = [
        "obj.__subclasses__()",
        "obj.__globals__",
        "obj.__builtins__",
        "obj.__dict__",
    ]
    for code in bad_codes:
        is_valid, msg = _validate_python_code(code)
        assert not is_valid, f"Expected '{code}' to be invalid"
        assert "Blocked: access to forbidden attribute" in msg

def test_getattr_bypass():
    # Dynamic attribute access via getattr
    code = "getattr(obj, 'sub' + 'classes')"
    is_valid, msg = _validate_python_code(code)
    assert not is_valid
    assert "Blocked: dynamic attribute access via getattr" in msg

    # Forbidden attribute via literal string in getattr
    code = "getattr(obj, '__globals__')"
    is_valid, msg = _validate_python_code(code)
    assert not is_valid
    assert "Blocked: getattr access to forbidden attribute" in msg

    # Legitimate getattr
    code = "getattr(obj, 'some_legit_attr')"
    is_valid, msg = _validate_python_code(code)
    assert is_valid

def test_obfuscated_imports():
    # Regex would miss this
    code = "o = __import__('o' + 's')\no.system('ls')"
    is_valid, msg = _validate_python_code(code)
    assert not is_valid
    assert "__import__" in msg or "os" in msg

def test_syntax_error():
    code = "this is not python code"
    is_valid, msg = _validate_python_code(code)
    assert not is_valid
    assert "Syntax error" in msg
