## 2026-04-27 - Command Injection and Path Traversal in TerminalTool
**Vulnerability:** `TerminalTool` allowed command chaining (e.g., `&&`, `;`) to bypass the allowed command list and permitted path traversal (e.g., `../../../secret.txt`) in command arguments to access files outside the workspace.
**Learning:** Simple string splitting or naive tokenization fails to account for shell operators and argument-level path traversal. `shlex.shlex` with `punctuation_chars=True` is necessary for accurate shell command parsing.
**Prevention:** Always tokenize shell commands using a proper shell lexer and validate every command in a chain. Use `is_safe_path` to validate all tokens that look like paths against the intended workspace.
