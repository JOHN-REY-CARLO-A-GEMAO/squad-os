
import pytest
from squad_os.tools.registry import _validate_python_code

def test_validate_python_code_bypass():
    # Simple bypasses for regex-based validation

    # 1. Aliasing
    code_aliasing = "import os as o\no.system('echo VULNERABLE')"
    is_valid, msg = _validate_python_code(code_aliasing)
    assert not is_valid, f"Bypass successful with aliasing! Message: {msg}"
    assert "Blocked" in msg

    # 2. getattr
    code_getattr = "import os\ngetattr(os, 'system')('echo VULNERABLE')"
    is_valid, msg = _validate_python_code(code_getattr)
    assert not is_valid, f"Bypass successful with getattr! Message: {msg}"
    assert "Blocked" in msg

    # 3. String concatenation (blocked by non-literal getattr)
    code_concat = "import os\nfunc = 'sys' + 'tem'\ngetattr(os, func)('echo VULNERABLE')"
    is_valid, msg = _validate_python_code(code_concat)
    assert not is_valid, f"Bypass successful with string concatenation! Message: {msg}"
    assert "non-literal" in msg

def test_validate_python_code_advanced_bypass():
    # 4. From import
    code_from = "from os import system as s\ns('echo VULNERABLE')"
    is_valid, msg = _validate_python_code(code_from)
    assert not is_valid, f"Bypass successful with from import aliasing! Message: {msg}"
    assert "alias" in msg

    # 5. Nested attributes
    code_nested = "import os\nos.path.os.system('echo VULNERABLE')"
    is_valid, msg = _validate_python_code(code_nested)
    assert not is_valid, f"Bypass successful with nested attributes! Message: {msg}"
    assert "Blocked" in msg

    # 6. Built-in access via attribute
    code_builtin_attr = "import os\nos.eval('1+1')"
    is_valid, msg = _validate_python_code(code_builtin_attr)
    assert not is_valid, f"Bypass successful with built-in via attribute! Message: {msg}"
    assert "forbidden" in msg

    # 7. Sensitive attributes (jailbreak)
    code_jailbreak = "().__class__.__base__.__subclasses__()"
    is_valid, msg = _validate_python_code(code_jailbreak)
    assert not is_valid, f"Bypass successful with jailbreak attribute! Message: {msg}"
    assert "sensitive" in msg

def test_validate_python_code_safe():
    # 8. Safe code
    code_safe = "import os\nprint(os.path.join('a', 'b'))"
    is_valid, msg = _validate_python_code(code_safe)
    assert is_valid, f"Safe code blocked! Message: {msg}"

    code_safe_math = "import math\nmath.sqrt(16)"
    is_valid, msg = _validate_python_code(code_safe_math)
    assert is_valid, f"Safe math code blocked! Message: {msg}"
