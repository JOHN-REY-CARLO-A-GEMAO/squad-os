# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-06-02 - Python Sandbox Regex Bypass
**Vulnerability:** Regex-based validation of Python code was easily bypassed using module aliases (e.g., `import os as o`), direct imports (e.g., `from os import system`), and dynamic attribute access via `getattr`.
**Learning:** Simple string or regex matching is insufficient for securing code execution. Attackers can use various language features to obfuscate malicious calls.
**Prevention:** Use Abstract Syntax Tree (AST) analysis to inspect the code's structure. Track imports and aliases, block dangerous modules and built-ins at the node level, and restrict access to sensitive internal attributes (like `__subclasses__`). Ensure dynamic access functions like `getattr` are also validated.
