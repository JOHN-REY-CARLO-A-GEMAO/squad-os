## 2026-05-17 - Path Traversal in Terminal Commands
**Vulnerability:** TerminalTool allowed execution of commands with arguments pointing outside the workspace (e.g., `cat ../../../etc/passwd`).
**Learning:** Even if the command itself is allowed (e.g., `cat`), its arguments must be validated for path traversal. `shlex.shlex(punctuation_chars=True)` provides a more robust way to parse shell-like commands compared to naive regex splitting.
**Prevention:** Always validate all tokens in a terminal command that look like paths against the designated workspace using `is_safe_path`.
