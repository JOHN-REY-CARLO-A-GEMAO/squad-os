# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-06-09 - Robust Python Sanitization via AST
**Vulnerability:** Regex-based Python code validation was easily bypassed using module aliasing (e.g., `import os as o`), indirect imports (`from os import system`), or assigning built-ins to variables (`x = eval`).
**Learning:** Static regex patterns cannot capture the stateful nature of Python's import system and name binding. A proper security visitor must track aliases and imported names to maintain a robust blocklist.
**Prevention:** Use `ast.NodeVisitor` to maintain a mapping of local names to their true sources. Explicitly block built-in references in `visit_Name` to prevent secondary aliasing of restricted functions.
