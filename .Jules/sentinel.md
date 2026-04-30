## 2025-05-15 - [Chained Command Injection Bypass]
**Vulnerability:** Command injection via shell operators (;, &&, ||, |, &) in terminal tools.
**Learning:** Simple string splitting or standard `shlex.split` only validates the first command in a sequence. Shell operators allow executing additional, unvalidated commands.
**Prevention:** Use `shlex.shlex(io.StringIO(command), punctuation_chars=True)` to properly tokenize shell operators. Implement a state machine or loop that treats every token following a separator as a new base command to be validated against an allowlist. Avoid blanket allowance of relative paths like `./` if the agent has file-writing capabilities.
