# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-06-19 - Python Sandbox Escape via Regex Bypasses
**Vulnerability:** The regex-based Python code validator was easily bypassed using `getattr()`, string concatenation for module names in `__import__`, and dunder attribute access like `__subclasses__`.
**Learning:** Regex is insufficient for validating code structure. Attackers can use dynamic attribute access and string manipulation to reconstruct dangerous calls that regex won't match.
**Prevention:** Use AST (Abstract Syntax Tree) analysis to validate code. The `ast.NodeVisitor` can track module aliases, block forbidden built-ins regardless of how they are called, and globally restrict access to sensitive attributes/methods (e.g., `system`, `popen`) and dunder attributes.
