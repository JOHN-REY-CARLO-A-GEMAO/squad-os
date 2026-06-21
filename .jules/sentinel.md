# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-06-21 - Python Sandbox Escape via Aliasing
**Vulnerability:** Regex-based validation failed to catch forbidden module usage when aliased (e.g., 'import os as o') or accessed dynamically (e.g., 'getattr(__import__("os"), "system")').
**Learning:** Static string analysis is insufficient for Python security. AST-based analysis is required to track module aliases and detect forbidden built-ins in complex expressions.
**Prevention:** Use ast.NodeVisitor to track the state of imports and aliases throughout the code, and block access to sensitive built-ins like 'getattr' and '__import__' that enable dynamic bypasses.
