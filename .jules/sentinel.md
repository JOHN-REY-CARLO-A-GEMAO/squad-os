# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-06-04 - Python Validation Regex Bypass
**Vulnerability:** Regex-based Python code validation in `_validate_python_code` was bypassed using aliased imports (e.g., `import os as o`), direct function imports (e.g., `from os import system`), and dynamic attribute access via `getattr`.
**Learning:** Simple string matching or regex is insufficient for securing code execution environments because it cannot account for Python's flexible syntax and dynamic nature.
**Prevention:** Use Abstract Syntax Tree (AST) analysis to inspect code structure. Track module and function aliases throughout the tree to ensure security policies are applied regardless of how a resource is named.
