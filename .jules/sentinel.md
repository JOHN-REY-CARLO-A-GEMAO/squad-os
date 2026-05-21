## 2025-05-15 - Command Injection and Path Traversal in TerminalTool

**Vulnerability:** The `TerminalTool` was vulnerable to command injection through shell operators (`;`, `&&`, `||`, `|`, `&`) because it only validated the very first token and the first token after a pipe. It was also vulnerable to path traversal (e.g., `cat ../../../etc/passwd`) because it didn't validate command arguments against the workspace.

**Learning:** Simple string splitting or only checking the start of a command is insufficient for security validation of shell commands. Shells have many ways to chain commands, and every segment must be treated as a potential new command. Furthermore, even "safe" commands like `cat` or `ls` can be used to leak sensitive data if their arguments are not restricted to a safe sandbox.

**Prevention:** Always use a robust parser like `shlex` to tokenize shell inputs. Implement a stateful validation loop that identifies all command initiation points (start of string, after operators). For every token that represents a file path, explicitly verify it using a traversal-resistant utility like `is_safe_path` against the intended workspace.
