# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-06-07 - Regex-based Python Code Validation Bypass
**Vulnerability:** Python code validation used brittle regex patterns that were easily bypassed using module aliasing (e.g., `import os as o`), dynamic attribute access (e.g., `getattr(os, 'system')`), or string concatenation in `__import__`.
**Learning:** Regex is insufficient for validating dynamic languages like Python. AST-based analysis is required to track aliases and block forbidden built-ins and attributes reliably.
**Prevention:** Use `ast.NodeVisitor` to implement a robust security scanner. Maintain a strict blocklist of forbidden built-ins (including `getattr`, `setattr`, `delattr`), forbidden internal attributes (e.g., `__subclasses__`), and dangerous modules/methods.
