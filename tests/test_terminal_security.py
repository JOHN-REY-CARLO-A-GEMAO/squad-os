import pytest
from squad_os.tools.registry import _validate_terminal_command

@pytest.mark.parametrize("command,expected_valid", [
    ("ls", True),
    ("ls -la", True),
    ("echo hello", True),
    ("echo hello > output.txt", True),
    ("ls | grep pattern", True),
    ("ls && echo done", True),
    ("/bin/ls", True),
    ("./myprog", True),
    ("unknown_cmd", False),
    ("ls ; unknown_cmd", False),
    ("ls && unknown_cmd", False),
    ("ls || unknown_cmd", False),
    ("echo hi | unknown_cmd", False),
    ("unknown_cmd | grep pattern", False),
    ("rm -rf /", False),
    ("ls ; rm -rf /", False),
    ("echo secret > /etc/passwd", False),
    ("echo hi > safe.txt", True),
])
def test_terminal_security_validation(command, expected_valid):
    is_valid, _ = _validate_terminal_command(command)
    assert is_valid == expected_valid
