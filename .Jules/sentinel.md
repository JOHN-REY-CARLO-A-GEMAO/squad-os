## 2026-04-25 - Terminal Command Injection via Shell Operators
**Vulnerability:** Command injection in `TerminalTool` allowed executing arbitrary commands by chaining them with shell operators like `;`, `&&`, `||`, and `|` (e.g., `ls ; whoami`).
**Learning:** The previous validation only checked the first part of a command string, assuming it was a single command. Attackers could hide malicious commands after separators. `shlex.split` or simple string splitting is insufficient for security validation of shell command lines.
**Prevention:** Use `shlex.shlex` with `punctuation_chars=True` to properly tokenize shell command lines. Iterate through all tokens and verify that every token following a shell operator is a validated command from the allowlist.
