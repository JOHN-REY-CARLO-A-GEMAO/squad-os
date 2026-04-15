## 2026-04-15 - Command Injection via Chaining
**Vulnerability:** TerminalTool was vulnerable to command injection via shell operators (&&, ;, |, etc.) because it only validated the first word of the entire command string.
**Learning:** Naive splitting of shell commands (e.g., cmd.split('|')) is insufficient. Attackers can use multiple operators, and operators can be hidden inside quotes or backslashes.
**Prevention:** Use shlex.split to tokenize the full command and validate every token that follows a shell operator against an allowlist.
