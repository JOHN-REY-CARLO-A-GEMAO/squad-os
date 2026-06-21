import pytest
from squad_os.tools.registry import _validate_python_code

class TestPythonSecurityUpgrade:
    @pytest.mark.parametrize("code,expected_blocked", [
        ("import os as o; o.system('ls')", "os"),
        ("getattr(__import__('os'), 'system')('ls')", "getattr"),
        ("(eval)('os.system(\"ls\")')", "eval"),
        ("import os.path; print(os.path.exists('/'))", "os"),
        ("import socket; s = socket.socket()", "socket"),
        ("from builtins import eval as e; e('1')", "eval"),
    ])
    def test_blocks_malicious_code(self, code, expected_blocked):
        valid, msg = _validate_python_code(code)
        assert not valid
        assert expected_blocked.lower() in msg.lower()

    def test_allows_safe_code(self):
        valid, msg = _validate_python_code("print('Safe'); x = 1 + 1")
        assert valid, msg
