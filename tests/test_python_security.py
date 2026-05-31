import pytest
from squad_os.tools.registry import _validate_python_code

class TestPythonSecurityBypass:
    """Tests for potential bypasses of Python code validation."""

    def test_alias_bypass(self):
        # Current regex-based validation might miss this if it only looks for "os.system"
        code = """
import os as o
o.system('ls')
"""
        valid, msg = _validate_python_code(code)
        # We EXPECT this to be blocked by a robust validator
        # But if it's currently True (valid), it confirms the bypass
        assert valid is False, f"Bypass successful: alias 'o.system' was not blocked. Msg: {msg}"

    def test_direct_import_bypass(self):
        code = """
from os import system
system('ls')
"""
        valid, msg = _validate_python_code(code)
        assert valid is False, f"Bypass successful: direct import 'system' was not blocked. Msg: {msg}"

    def test_dynamic_attribute_bypass(self):
        code = """
import os
getattr(os, 'system')('ls')
"""
        valid, msg = _validate_python_code(code)
        assert valid is False, f"Bypass successful: dynamic attribute 'getattr' was not blocked. Msg: {msg}"

    def test_sandbox_escape_bypass(self):
        code = """
# Classic sandbox escape payload
().__class__.__base__.__subclasses__()[0].__init__.__globals__['os'].system('ls')
"""
        valid, msg = _validate_python_code(code)
        assert valid is False, f"Bypass successful: sandbox escape payload was not blocked. Msg: {msg}"

    def test_multiline_bypass(self):
        code = """
os. \\
system('ls')
"""
        valid, msg = _validate_python_code(code)
        assert valid is False, f"Bypass successful: multiline 'os.system' was not blocked. Msg: {msg}"

    def test_normal_code_allowed(self):
        code = """
def hello(name):
    print(f"Hello, {name}!")

hello("World")
"""
        valid, msg = _validate_python_code(code)
        assert valid is True, f"Normal code was incorrectly blocked: {msg}"
