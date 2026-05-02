## 2025-05-02 - Command Injection via Shell Operator Chaining

**Vulnerability:** The `_validate_terminal_command` function used a simple `split('|')` to check for sub-commands, which allowed bypassing the allowlist using other shell operators like `;`, `&&`, `||`, and `&`. An attacker could execute unauthorized commands by appending them after a valid one (e.g., `ls ; cat /etc/passwd`).

**Learning:** Simple string splitting is insufficient for parsing shell commands which have complex grammars and multiple command separators. Relying on partial parsing leads to significant security gaps.

**Prevention:** Use a robust lexer like `shlex` with `punctuation_chars=True` to correctly tokenize and identify all command boundaries. Every identified command in a chain must be validated against the allowlist. Additionally, validate all path-like arguments using a dedicated `is_safe_path` utility.
