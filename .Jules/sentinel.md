## 2026-05-10 - Shell Command Injection via Chaining
**Vulnerability:** The `TerminalTool` command validation only checked the first token of the entire command string. This allowed an attacker to chain authorized commands with unauthorized ones using shell operators like `&&`, `;`, or `|`.
**Learning:** `shlex.split()` is insufficient for validating shell commands that may contain multiple execution contexts. `shlex.shlex` with `punctuation_chars=True` is necessary to properly tokenize and validate every sub-command in a chain.
**Prevention:** Always use a tokenizer that recognizes shell punctuation and iterate through all potential command starts (after `;`, `&&`, etc.) to ensure every executed command is within the allowlist.
