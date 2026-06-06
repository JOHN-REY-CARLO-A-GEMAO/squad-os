# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-06-06 - Robust AST-based Python Validation
**Vulnerability:** Regex-based Python code validation was easily bypassed using aliased imports (e.g., `import os as o`), from-imports, or dynamic attribute access (e.g., `getattr(os, "system")`).
**Learning:** Regular expressions are insufficient for validating code that can be obfuscated via aliasing or dynamic resolution. AST analysis is necessary to track the actual intent and origin of function calls.
**Prevention:** Use a robust AST visitor that tracks module aliases and imported names, blocks access to forbidden internal attributes (e.g., `__subclasses__`), and enforces literal string arguments for dynamic resolution functions like `getattr`.
