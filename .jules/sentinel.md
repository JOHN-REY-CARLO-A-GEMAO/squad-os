# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-05-28 - Python Code Validation Bypass (Regex vs AST)
**Vulnerability:** Regex-based Python code validation was easily bypassed by simple whitespace variations (e.g., `os. system()`) or aliased imports (e.g., `import os as o; o.system()`).
**Learning:** For dynamic languages like Python, regex is insufficient for security validation. Abstract Syntax Tree (AST) analysis is required to understand the actual structure and intent of the code regardless of formatting. Furthermore, AST analysis must account for the scope of imports and aliases to be effective.
**Prevention:** Use the `ast` module to parse and inspect user-provided Python code. Track `Import` and `ImportFrom` nodes to map aliases back to their original modules and functions. Maintain a strict allowlist of built-ins and a denylist of dangerous module attributes.
