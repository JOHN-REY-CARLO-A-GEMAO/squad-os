## 2026-04-26 - Terminal Path Traversal via Command Arguments
**Vulnerability:** The `TerminalTool` allowed executing commands with path traversal sequences (e.g., `cat ../../../secret.txt`) in their arguments, enabling access to files outside the designated workspace.
**Learning:** While the tool was restricted to a specific `cwd`, shell commands can still reference paths relative to that directory or absolute paths on the system, bypassing intended sandbox boundaries if arguments are not validated.
**Prevention:** Always validate all tokens in a shell command that appear to be file paths (containing `..` or absolute path indicators) using a robust path validation utility like `is_safe_path` before execution.
