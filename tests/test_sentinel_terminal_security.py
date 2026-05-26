import os
import tempfile
import pytest
from squad_os.tools.registry import _validate_terminal_command

def temp_workspace():
    return tempfile.mkdtemp(prefix="squad_test_")

class TestSentinelPathTraversal:
    """Tests for Sentinel's ./ prefix path traversal fix."""

    def test_block_relative_escape_via_dot_slash(self):
        ws = temp_workspace()
        valid, msg = _validate_terminal_command("./../outside.sh", ws)
        assert not valid
        assert "Access denied" in msg

    def test_allow_dot_slash_in_workspace(self):
        ws = temp_workspace()
        inner = os.path.join(ws, "scripts")
        os.makedirs(inner, exist_ok=True)
        valid, msg = _validate_terminal_command("./scripts/deploy", ws)
        assert valid, f"Expected allowed, got: {msg}"

    def test_block_multiple_dot_slash_escape(self):
        ws = temp_workspace()
        valid, msg = _validate_terminal_command("./../../etc/passwd", ws)
        assert not valid
        assert "Access denied" in msg

    def test_block_dot_slash_with_chained_command(self):
        ws = temp_workspace()
        valid, msg = _validate_terminal_command("ls && ./../escape.sh", ws)
        assert not valid
        assert "Access denied" in msg

class TestSentinelAbsolutePath:
    """Tests for Sentinel's TRUSTED_SYSTEM_DIRS absolute path restriction."""

    def test_block_untrusted_absolute_path(self):
        ws = temp_workspace()
        valid, msg = _validate_terminal_command("/tmp/evil_script", ws)
        assert not valid
        assert "untrusted directory" in msg

    def test_block_untrusted_absolute_allowed_basename(self):
        ws = temp_workspace()
        valid, msg = _validate_terminal_command("/tmp/ls", ws)
        assert not valid
        assert "untrusted directory" in msg

    def test_allow_trusted_absolute_path(self):
        ws = temp_workspace()
        valid, msg = _validate_terminal_command("/bin/ls", ws)
        assert valid, f"Expected /bin/ls allowed, got: {msg}"

    def test_allow_trusted_absolute_path_usr_bin(self):
        ws = temp_workspace()
        valid, msg = _validate_terminal_command("/usr/bin/git", ws)
        assert valid, f"Expected /usr/bin/git allowed, got: {msg}"

    def test_block_trusted_dir_unknown_command(self):
        ws = temp_workspace()
        valid, msg = _validate_terminal_command("/bin/unknown_cmd_xyz", ws)
        assert not valid
        assert "not in allowed list" in msg

    def test_block_trusted_dir_malformed_path(self):
        ws = temp_workspace()
        valid, msg = _validate_terminal_command("/usr/../bin/ls", ws)
        assert not valid
        assert "untrusted directory" in msg or "Access denied" in msg

class TestSentinelRelativeQualifiedPath:
    """Tests for Sentinel's relative qualified path validation (paths with / or \\)."""

    def test_block_relative_escape_with_separator(self):
        ws = temp_workspace()
        valid, msg = _validate_terminal_command("subdir/../../../etc/passwd", ws)
        assert not valid
        assert "Access denied" in msg

    def test_allow_safe_relative_path(self):
        ws = temp_workspace()
        inner = os.path.join(ws, "tools")
        os.makedirs(inner, exist_ok=True)
        valid, msg = _validate_terminal_command("tools/python", ws)
        assert valid, f"Expected allowed, got: {msg}"

    def test_block_relative_path_with_forbidden_command(self):
        ws = temp_workspace()
        valid, msg = _validate_terminal_command("tools/some_random_tool", ws)
        assert not valid

class TestSentinelNormalCommands:
    """Tests that normal commands still work."""

    def test_simple_allowed_command(self):
        ws = temp_workspace()
        valid, msg = _validate_terminal_command("ls", ws)
        assert valid, f"Expected ls allowed, got: {msg}"

    def test_allowed_command_with_flags(self):
        ws = temp_workspace()
        valid, msg = _validate_terminal_command("ls -la", ws)
        assert valid, f"Expected ls -la allowed, got: {msg}"

    def test_blocked_unknown_command(self):
        ws = temp_workspace()
        valid, msg = _validate_terminal_command("some_random_cmd", ws)
        assert not valid
        assert "not in allowed list" in msg

    def test_safe_chained_commands(self):
        ws = temp_workspace()
        valid, msg = _validate_terminal_command("ls && pwd && echo hello", ws)
        assert valid, f"Expected chained allowed, got: {msg}"

    def test_empty_command(self):
        ws = temp_workspace()
        valid, msg = _validate_terminal_command("", ws)
        assert not valid
        assert "Empty command" in msg
