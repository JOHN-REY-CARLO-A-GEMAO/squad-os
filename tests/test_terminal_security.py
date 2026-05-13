import pytest
from squad_os.tools.registry import _validate_terminal_command
import os

def test_validate_terminal_command_basic():
    # Test allowed commands
    assert _validate_terminal_command("ls")[0] == True
    assert _validate_terminal_command("whoami")[0] == True
    assert _validate_terminal_command("pwd")[0] == True

def test_validate_terminal_command_not_allowed():
    # Test unallowed commands
    assert _validate_terminal_command("sleep 1")[0] == False
    assert "not in allowed command list" in _validate_terminal_command("sleep 1")[1]

def test_validate_terminal_command_multiple():
    # Test multiple commands with ;
    assert _validate_terminal_command("ls ; whoami")[0] == True
    assert _validate_terminal_command("ls ; sleep 1")[0] == False

    # Test multiple commands with &&
    assert _validate_terminal_command("ls && whoami")[0] == True
    assert _validate_terminal_command("ls && sleep 1")[0] == False

    # Test multiple commands with |
    assert _validate_terminal_command("ls | grep test")[0] == True
    assert _validate_terminal_command("ls | sleep 1")[0] == False

def test_validate_terminal_command_traversal():
    workspace = os.path.realpath("workspace")
    if not os.path.exists(workspace):
        os.makedirs(workspace, exist_ok=True)

    # Test path traversal in arguments
    assert _validate_terminal_command("ls ..", workspace)[0] == False
    assert "outside the workspace" in _validate_terminal_command("ls ..", workspace)[1]

    # Test absolute path traversal
    assert _validate_terminal_command("ls /etc", workspace)[0] == False

    # Test safe path
    assert _validate_terminal_command("ls .", workspace)[0] == True

def test_validate_terminal_command_redirection():
    workspace = os.path.realpath("workspace")

    # Redirection to safe path (in theory shlex treats > as punctuation)
    # Our current implementation treats tokens after operators as arguments if they are not command operators
    # and checks them for path traversal if they look like paths.

    assert _validate_terminal_command("ls > output.txt", workspace)[0] == True
    assert _validate_terminal_command("ls > /tmp/test.txt", workspace)[0] == False

def test_validate_terminal_command_dangerous():
    assert _validate_terminal_command("rm -rf /")[0] == False
    assert "dangerous patterns" in _validate_terminal_command("rm -rf /")[1]
