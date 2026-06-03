# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-06-02 - Python Validation Regex Bypass
**Vulnerability:** The Python code validator used regex to detect dangerous patterns (e.g., `os.system`). This was easily bypassed by using module aliases (e.g., `import os as o; o.system('ls')`) or dynamic attribute access (e.g., `getattr(os, 'system')`).
**Learning:** Regex is insufficient for validating dynamic languages like Python. Static analysis of the Abstract Syntax Tree (AST) is required to reliably track imports, aliases, and attribute access across the codebase.
**Prevention:** Always use AST-based validation for Python code execution sandboxes. Track aliased imports and block dynamic attribute access (`getattr`, `setattr`) with non-literal strings to prevent obfuscated malicious calls.
