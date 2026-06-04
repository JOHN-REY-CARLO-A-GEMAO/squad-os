import pytest
from squad_os.tools.registry import _validate_python_code

@pytest.mark.parametrize("code,expected_valid,expected_message_part", [
    # Safe code
    ("print('hello world')", True, ""),
    ("x = 1 + 2\ny = [i for i in range(10)]", True, ""),
    ("def my_func(a, b): return a + b", True, ""),
    ("import math\nprint(math.sqrt(16))", True, ""),
    ("import json\ndata = json.loads('{\"a\": 1}')", True, ""),

    # Dangerous Imports
    ("import os", False, "Blocked: import of dangerous module 'os'"),
    ("import os as o", False, "Blocked: import of dangerous module 'os'"),
    ("from os import system", False, "Blocked: import from dangerous module 'os'"),
    ("import subprocess", False, "Blocked: import of dangerous module 'subprocess'"),
    ("import sys", False, "Blocked: import of dangerous module 'sys'"),
    ("import shutil", False, "Blocked: import of dangerous module 'shutil'"),
    ("import socket", False, "Blocked: import of dangerous module 'socket'"),
    ("import requests", False, "Blocked: import of dangerous module 'requests'"),
    ("import aiohttp", False, "Blocked: import of dangerous module 'aiohttp'"),
    ("import httpx", False, "Blocked: import of dangerous module 'httpx'"),
    ("import importlib", False, "Blocked: import of dangerous module 'importlib'"),

    # Forbidden Built-ins
    ("eval('1+1')", False, "Blocked: use of forbidden built-in 'eval'"),
    ("exec('print(1)')", False, "Blocked: use of forbidden built-in 'exec'"),
    ("compile('a=1', '', 'exec')", False, "Blocked: use of forbidden built-in 'compile'"),
    ("__import__('os')", False, "Blocked: use of forbidden built-in '__import__'"),
    ("open('file.txt', 'w')", False, "Blocked: use of forbidden built-in 'open'"),
    ("input('Enter something: ')", False, "Blocked: use of forbidden built-in 'input'"),
    ("globals()", False, "Blocked: use of forbidden built-in 'globals'"),

    # Dangerous Method Calls
    ("os.system('ls')", False, "Blocked: call to dangerous method 'os.system'"),
    ("import os; os.popen('ls')", False, "Blocked: import of dangerous module 'os'"),
    ("import subprocess; subprocess.run(['ls'])", False, "Blocked: import of dangerous module 'subprocess'"),

    # Forbidden Attributes
    ("obj.__subclasses__()", False, "Blocked: access to forbidden attribute '__subclasses__'"),
    ("obj.__globals__", False, "Blocked: access to forbidden attribute '__globals__'"),
    ("obj.__builtins__", False, "Blocked: access to forbidden attribute '__builtins__'"),
    ("obj.__dict__", False, "Blocked: access to forbidden attribute '__dict__'"),
    ("obj.__class__", False, "Blocked: access to forbidden attribute '__class__'"),
    ("obj.__base__", False, "Blocked: access to forbidden attribute '__base__'"),

    # Dynamic access with getattr
    ("getattr(obj, 'system')", False, "Blocked: dynamic access to forbidden attribute 'system'"),
    ("getattr(obj, '__subclasses__')", False, "Blocked: dynamic access to forbidden attribute '__subclasses__'"),
    ("getattr(obj, 'any' + 'thing')", False, "Blocked: getattr() with non-literal attribute name"),

    # Aliasing Bypasses
    ("import os as o; o.system('ls')", False, "Blocked: import of dangerous module 'os'"),
    ("from os import system as s; s('ls')", False, "Blocked: import from dangerous module 'os'"),

    # Malformed Code
    ("import os", False, "Blocked: import of dangerous module 'os'"),
    ("if True:", False, "Syntax error in Python code"),
])
def test_validate_python_code(code, expected_valid, expected_message_part):
    valid, message = _validate_python_code(code)
    assert valid == expected_valid
    if not valid:
        assert expected_message_part in message
