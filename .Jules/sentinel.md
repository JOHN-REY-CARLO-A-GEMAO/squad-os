## 2026-04-19 - Improved Command Injection Mitigation in TerminalTool
**Vulnerability:** Command injection was possible in `TerminalTool` by using shell operators like `;`, `&&`, or `||` to chain unauthorized commands after an allowed one.
**Learning:** Simple string splitting or basic prefix checks are insufficient for validating shell commands, as attackers can use various operators to execute multiple commands in a single string.
**Prevention:** Use `shlex.shlex(punctuation_chars=True)` to properly tokenize commands according to shell rules, and validate every command sequence (following an operator) against a strict allowlist.
