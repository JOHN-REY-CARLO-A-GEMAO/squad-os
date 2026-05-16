## 2025-05-15 - Terminal Command Path Traversal Validation
**Vulnerability:** Terminal commands were validated only for the base command allowlist, but arguments (files, paths) were not checked for path traversal.
**Learning:** Validating only the base command is insufficient when the command accepts file paths as arguments. Chained commands (e.g., using `&&` or `|`) also need recursive validation of each sub-command.
**Prevention:** Use `shlex.split` to tokenize full commands, validate each sub-command against an allowlist, and verify every token that could be a path using a robust `is_safe_path` utility against the workspace boundary.
