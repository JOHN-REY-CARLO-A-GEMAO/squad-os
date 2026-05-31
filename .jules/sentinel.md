# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-05-31 - Python Sandbox Escape via Aliasing and Dynamic Access
**Vulnerability:** Regex-based Python code validation was easily bypassed using module aliasing (`import os as o`), direct function imports (`from os import system`), multiline splitting, and dynamic attribute access (`getattr(os, 'system')`).
**Learning:** Static analysis of code using Regular Expressions is insufficient for security because it cannot track variable state or handle the syntactic flexibility of languages like Python. AST-based analysis is required to reliably track imports and resolve calls.
**Prevention:** Always use AST-based validation for code execution sandboxes. Track module and function aliases, and strictly restrict dynamic attribute access (e.g., `getattr`) to literal string keys that are not in a forbidden list.
