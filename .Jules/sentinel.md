## 2026-04-12 - [Robust Terminal Command Validation]
**Vulnerability:** Command injection bypass via unsplit shell operators and subshells.
**Learning:** Simple string splitting or regex-based splitting on shell operators (like `|`) is insufficient as it misses other operators (`;`, `&&`, `||`) and doesn't respect shell quoting, leading to either security gaps or functional regressions.
**Prevention:** Use `shlex.split` to properly parse the command line according to shell rules. Iterate through the resulting parts and strictly enforce that any part following a shell operator (or an inline `;`) must be an allowed command from the allowlist. Explicitly block redirections and subshell patterns (`$(...)`, `` `...` ``).
