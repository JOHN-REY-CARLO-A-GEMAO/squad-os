import os
import pytest
import io
import shlex
from squad_os.tools.registry import _validate_terminal_command

@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    return str(ws)

@pytest.mark.parametrize("command,expected_valid", [
    ("ls", True),
    ("ls | grep test", True),
    ("ls ; cat /etc/passwd", False),
    ("ls && cat /etc/passwd", False),
    ("ls || cat /etc/passwd", False),
    ("cat /etc/passwd", False),
    ("ls ../../../etc/passwd", False),
    ("sudo ls", False),
    ("ls > /tmp/hack", False),
])
def test_terminal_security_validation(command, expected_valid, workspace):
    is_valid, msg = _validate_terminal_command(command, workspace)
    assert is_valid == expected_valid, f"Command '{command}' validation failed: {msg}"

def test_terminal_valid_workspace_path(workspace):
    test_file = os.path.join(workspace, "test.txt")
    with open(test_file, "w") as f:
        f.write("test")

    is_valid, msg = _validate_terminal_command(f"cat {test_file}", workspace)
    assert is_valid is True, f"Valid workspace path was rejected: {msg}"
