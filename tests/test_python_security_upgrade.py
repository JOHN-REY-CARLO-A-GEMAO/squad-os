import pytest
from squad_os.tools.registry import _validate_python_code

class TestPythonSecurityUpgrade:
    """Tests for the upgraded AST-based Python code validator."""

    def test_basic_blocked_calls(self):
        codes = [
            "import os\nos.system('ls')",
            "import subprocess\nsubprocess.run(['ls'])",
            "eval('1+1')",
            "exec('print(1)')",
        ]
        for code in codes:
            valid, msg = _validate_python_code(code)
            assert not valid, f"Expected '{code}' to be blocked"

    def test_getattr_bypass(self):
        codes = [
            "import os\ngetattr(os, 'system')('ls')",
            "import os\ngetattr(os, 'sys' + 'tem')('ls')",
        ]
        for code in codes:
            valid, msg = _validate_python_code(code)
            assert not valid, f"Expected getattr bypass '{code}' to be blocked"

    def test_import_bypass(self):
        codes = [
            "__import__('os').system('ls')",
            "m = __import__('o' + 's')\nm.system('ls')",
        ]
        for code in codes:
            valid, msg = _validate_python_code(code)
            assert not valid, f"Expected import bypass '{code}' to be blocked"

    def test_alias_bypass(self):
        codes = [
            "import os as o\no.system('ls')",
            "from os import system as s\ns('ls')",
        ]
        for code in codes:
            valid, msg = _validate_python_code(code)
            assert not valid, f"Expected alias bypass '{code}' to be blocked"

    def test_submodule_import(self):
        codes = [
            "import os.path",
            "from os.path import exists",
        ]
        for code in codes:
            valid, msg = _validate_python_code(code)
            assert not valid, f"Expected submodule import '{code}' to be blocked"

    def test_dunder_bypass(self):
        codes = [
            "().__class__.__base__.__subclasses__()[0]",
            "object.__subclasses__()",
        ]
        for code in codes:
            valid, msg = _validate_python_code(code)
            assert not valid, f"Expected dunder bypass '{code}' to be blocked"

    def test_safe_code(self):
        codes = [
            "print('Hello, World!')",
            "x = [1, 2, 3]\ny = sum(x)",
            "import math\nmath.sqrt(16)",
            "def add(a, b): return a + b",
        ]
        for code in codes:
            valid, msg = _validate_python_code(code)
            assert valid, f"Expected safe code '{code}' to be allowed, but got: {msg}"
