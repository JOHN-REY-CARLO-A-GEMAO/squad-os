import pytest
from squad_os.tools.registry import _validate_terminal_command

@pytest.mark.parametrize("command, expected_valid", [
    ("ls", True),
    ("ls -la", True),
    ("pwd", True),
    ("ls && whoami", True),
    ("ls ; whoami", True),
    ("ls | grep test", True),
    ("ls || echo fail", True),
    ('grep "foo;bar" file.txt', True), # quoting respect
    ("echo 'Hello && Goodbye'", True), # quoting respect
    ("ls > /tmp/out", False), # redirection blocked
    ("ls 2>&1", False), # redirection blocked
    ("echo $(whoami)", False), # subshell blocked
    ("echo `whoami`", False), # subshell blocked
    ("ls; sleep 10", False), # sleep not in allowlist
    ("python -c 'import os; os.system(\"whoami\")'", True), # Now allowed because it's just python with args
    ("echo hello || rm -rf /", False), # dangerous pattern
    ("cat /etc/passwd", True), # cat is allowed
    ("cat /etc/passwd; rm -rf /", False), # dangerous pattern in second part
    ("ls && (whoami)", False), # ( is not allowed in base_cmd
    ("./my_script.sh", True), # starts with ./ is allowed
    ("/bin/ls", True), # qualified path to allowed command
    ("/usr/bin/python3", True), # qualified path to allowed command
    ("/bin/rm -rf /", False), # qualified path to allowed command BUT dangerous pattern
])
def test_validate_terminal_command(command, expected_valid):
    is_valid, error_msg = _validate_terminal_command(command)
    assert is_valid == expected_valid, f"Command: {command}, Error: {error_msg}"

def test_validate_terminal_command_empty():
    is_valid, _ = _validate_terminal_command("")
    assert is_valid == False
    is_valid, _ = _validate_terminal_command("   ")
    assert is_valid == False
