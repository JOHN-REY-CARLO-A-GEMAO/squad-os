# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-06-08 - Python Sandbox Escape via AST Analysis
**Vulnerability:** Regex-based Python code validation was bypassable using aliased imports (e.g., `import os as o`) and dynamic attribute access (e.g., `getattr(os, "system")`).
**Learning:** Regular expressions are insufficient for validating the security of programming languages where a single action can be expressed in many semantically equivalent ways. AST analysis provides a more reliable way to enforce security policies by inspecting the actual structure of the code.
**Prevention:** Always use AST-based validation for dynamic code execution. Track module and function aliases to prevent bypasses and block critical built-ins like `getattr` and `__import__`.
