import asyncio
import sys
import os

# Add the current directory to sys.path to import squad_os
sys.path.append(os.getcwd())

from squad_os.tools.registry import _validate_terminal_command

def test_validation():
    # Safe commands
    assert _validate_terminal_command("ls")[0] is True
    assert _validate_terminal_command("ls -la")[0] is True
    assert _validate_terminal_command("echo hello && ls")[0] is True
    assert _validate_terminal_command("ls ; pwd")[0] is True
    assert _validate_terminal_command("ls | grep foo")[0] is True

    # Bypasses that should now fail
    assert _validate_terminal_command("ls && bash")[0] is False
    assert _validate_terminal_command("echo hello ; sh")[0] is False
    # Use a command NOT in ALLOWED_COMMANDS
    assert _validate_terminal_command("pwd | topsecretcommand")[0] is False

    # Dangerous patterns
    assert _validate_terminal_command("rm -rf /")[0] is False
    assert _validate_terminal_command("ls && rm -rf /")[0] is False

    # Redirections
    assert _validate_terminal_command("ls > out.txt")[0] is True
    assert _validate_terminal_command("cat < in.txt")[0] is True
    assert _validate_terminal_command("ls 2> err.txt")[0] is True

    # Redirection with dangerous commands
    assert _validate_terminal_command("ls > /dev/null 2>&1")[0] is False # /dev/null is in DANGEROUS_PATTERNS

    print("All validation tests passed!")

if __name__ == "__main__":
    test_validation()
