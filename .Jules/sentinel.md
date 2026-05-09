## 2025-05-22 - Command Injection Bypass via Shell Operators

**Vulnerability:** The terminal tool's command validation only checked the first token of the entire string against an allowlist. This allowed attackers to bypass security by appending dangerous commands using shell operators like `&&`, `;`, `||`, or `|`. For example, `ls && bash` would pass because only `ls` was validated.

**Learning:** Simple string splitting or basic `shlex.split` is insufficient for validating multi-command shell inputs. Shell operators act as command separators, and each resulting segment must be treated as a new command for validation purposes.

**Prevention:** Use `shlex.shlex` with `punctuation_chars=True` to correctly tokenize shell commands including operators. Maintain state during tokenization to identify when a new command starts (after a shell operator) and validate every such command against the allowlist. Be careful to distinguish between command operators and redirection operators to avoid false positives on filenames.
