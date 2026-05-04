## 2026-05-04 - Terminal Command Injection via Shell Operators
**Vulnerability:** Terminal command validation only checked the first command in a chain or the first part of a pipe, allowing subsequent commands (e.g., after `;`, `&&`, `||`) to bypass the allowlist.
**Learning:** Simple string splitting or basic regex is insufficient for parsing shell commands which can contain complex chaining and redirection. `shlex.shlex` with `punctuation_chars=True` is necessary to correctly tokenize shell syntax.
**Prevention:** Always use a robust parser like `shlex` to decompose chained commands and validate EVERY resulting subcommand against the security allowlist. Ensure redirection operators are handled so their targets aren't mistaken for executable commands.
