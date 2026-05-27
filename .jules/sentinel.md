## 2025-05-25 - Terminal Execution Path Traversal and Absolute Path Bypass
**Vulnerability:** Found that the terminal validator allowed executing binaries outside the workspace if prefixed with `./` (e.g., `./../outside.sh`) and allowed any absolute path if the basename matched an allowed command (e.g., `/tmp/ls`).
**Learning:** Checking only the basename of a command for an allowlist is insufficient when the full path is user-controlled. Relative paths starting with `./` were previously exempted from `is_safe_path` checks.
**Prevention:** Always validate full command paths using `is_safe_path` for local executions and restrict absolute paths to a strict whitelist of trusted system directories.

## 2026-05-27 - Command Injection Pattern Bypass via Shell Pipes
**Vulnerability:** Dangerous command detection used literal substring matching, which was easily bypassed by adding spaces or using slightly different command structures (e.g., `curl ... | sh` was not blocked by `curl .*|.*sh`).
**Learning:** Security blocklists using literal strings are fragile. Attackers can use shell flexibility (extra whitespace, different redirections) to bypass them.
**Prevention:** Use regular expressions for pattern matching in security filters and include variations in whitespace (`\s+`) and common shell operators to increase robustness.
