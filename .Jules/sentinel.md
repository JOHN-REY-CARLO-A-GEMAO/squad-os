## 2025-05-15 - Command Injection via Shell Operators in Terminal Tool

**Vulnerability:** The `TerminalTool` command validation only checked the base command and piped commands (split by `|`), but failed to account for other shell operators like `;`, `&&`, `||`, and `&`. This allowed an attacker to chain arbitrary commands after an allowed base command.

**Learning:** `shlex.split()` or simple string splitting is insufficient for validating shell commands that might contain complex operators. Robust tokenization is required to identify all command entry points.

**Prevention:** Use `shlex.shlex(punctuation_chars=True)` to accurately tokenize shell commands and identify all shell operators. Every token following an operator must be treated as a new base command and validated against the allowlist.
