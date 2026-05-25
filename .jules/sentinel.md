## 2025-05-25 - Terminal Execution Path Traversal and Absolute Path Bypass
**Vulnerability:** Found that the terminal validator allowed executing binaries outside the workspace if prefixed with `./` (e.g., `./../outside.sh`) and allowed any absolute path if the basename matched an allowed command (e.g., `/tmp/ls`).
**Learning:** Checking only the basename of a command for an allowlist is insufficient when the full path is user-controlled. Relative paths starting with `./` were previously exempted from `is_safe_path` checks.
**Prevention:** Always validate full command paths using `is_safe_path` for local executions and restrict absolute paths to a strict whitelist of trusted system directories.
