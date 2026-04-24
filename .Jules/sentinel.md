## 2025-05-22 - Improved Terminal Command Validation
**Vulnerability:** Shell operator bypass in terminal command validation.
**Learning:** Simple string splitting or naive `shlex.split` is insufficient for validating shell commands that may contain operators like `&&`, `;`, `||`, `|`, and `&`. These operators allow chaining multiple commands, which can be used to bypass an allowlist that only checks the first token of the entire string.
**Prevention:** Use `shlex.shlex(command, posix=True, punctuation_chars=True)` to properly tokenize shell commands and identify all command entry points following shell operators. Each identified command must be validated against the allowlist.
