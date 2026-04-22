## 2026-04-22 - Command Injection and Bypass in TerminalTool

**Vulnerability:** Command injection via shell operators (`;`, `&&`, `||`, `&`) and dangerous pattern bypass using extra whitespace. The `TerminalTool` validation only checked the first command of a pipe chain and did not normalize whitespace before matching against blocked patterns like `rm -rf /`.

**Learning:** Shell command validation must account for all possible command separators, not just pipes. Using `shlex.shlex(punctuation_chars=True)` is more robust than manual string splitting for identifying sub-commands. Additionally, blocked patterns can be easily bypassed by simple string variations (like extra spaces) if the input is not normalized before comparison.

**Prevention:**
1. Use `shlex.shlex(punctuation_chars=True)` to accurately tokenize shell commands and identify all sub-commands in a chain.
2. Normalize whitespace in the command string (e.g., `re.sub(r'\s+', ' ', command)`) before performing pattern-based security checks.
3. Validate every single command in a chain against the allowlist, not just the first one.
