## 2025-05-15 - Path Traversal in Terminal Arguments
**Vulnerability:** The `TerminalTool` allowed arbitrary path traversal in command arguments (e.g., `cat ../../../secret.txt`) because it only validated the base command against an allowlist but did not inspect the arguments.
**Learning:** Security validation for terminal commands must go beyond just checking the executable. Arguments often contain file paths that can be used for unauthorized data access or modification.
**Prevention:** Use `shlex.split()` to parse the full command and validate every token that appears to be a path or contains traversal sequences against the allowed workspace using `is_safe_path()`.
