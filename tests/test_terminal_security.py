import pytest
from squad_os.tools.registry import _validate_terminal_command

@pytest.mark.parametrize("command, expected_valid", [
    ("ls", True),
    ("ls -la", True),
    ("ls ; whoami", True), # Both are allowed
    ("ls ; uname", False), # uname is not allowed
    ("ls && echo 'hi'", True), # echo is allowed
    ("ls && uname", False),
    ("ls | grep pattern", True), # grep is allowed
    ("ls | wall", False), # wall is not allowed
    ("cat file.txt", True),
    ("cat file.txt ; rm -rf /", False), # dangerous
    ("echo $(uname)", False), # subshell
    ("echo `uname`", False), # backticks
    ("./myscript.sh", True),
    ("/bin/ls", True),
    ("/usr/bin/uname", False),
])
def test_terminal_security_validation(command, expected_valid):
    is_valid, msg = _validate_terminal_command(command)
    assert is_valid == expected_valid, f"Command '{command}' validation failed: expected {expected_valid}, got {is_valid} ({msg})"
