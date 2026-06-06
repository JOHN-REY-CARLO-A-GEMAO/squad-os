import pytest
from squad_os.tools.registry import _validate_python_code

class TestPythonSecurityValidation:
    """Tests for Sentinel's AST-based Python code validation."""

    def test_block_simple_os_system(self):
        code = "import os; os.system('ls')"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "os.system" in msg.lower() or "dangerous module" in msg.lower()

    def test_block_aliased_import(self):
        # Current regex-based validation might miss this
        code = "import os as o; o.system('ls')"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "system" in msg.lower()

    def test_block_from_import(self):
        # Current regex-based validation might miss this
        code = "from os import system; system('ls')"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "system" in msg.lower()

    def test_block_dynamic_attribute_access(self):
        # Current regex-based validation might miss this
        code = "import os; getattr(os, 'system')('ls')"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "getattr" in msg.lower() or "system" in msg.lower()

    def test_block_internal_attribute_access(self):
        # Current regex-based validation might miss this
        code = "[].__class__.__base__.__subclasses__()"
        valid, msg = _validate_python_code(code)
        assert not valid
        assert "__subclasses__" in msg.lower() or "forbidden attribute" in msg.lower()

    def test_block_eval_exec(self):
        assert not _validate_python_code("eval('1+1')")[0]
        assert not _validate_python_code("exec('import os')")[0]

    def test_allow_safe_code(self):
        code = """
def hello(name):
    return f"Hello, {name}!"

print(hello("World"))
"""
        valid, msg = _validate_python_code(code)
        assert valid, f"Safe code should be allowed: {msg}"

    def test_allow_math_and_json(self):
        code = """
import math
import json

data = json.dumps({"result": math.sqrt(16)})
print(data)
"""
        valid, msg = _validate_python_code(code)
        assert valid, f"Math and JSON imports should be allowed: {msg}"
