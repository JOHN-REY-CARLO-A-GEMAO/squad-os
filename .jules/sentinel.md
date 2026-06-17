# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-06-17 - AST-Based Sandbox Escape Prevention
**Vulnerability:** Regex-based Python code validation is easily bypassed using aliasing (import os as o), string-based attribute access (getattr(os, "system")), or navigating the object hierarchy (.__subclasses__()).
**Learning:** Heuristic regexes cannot capture the recursive and dynamic nature of Python. AST analysis provides a more robust structure for security validation by inspecting the actual intent of the code (imports, calls, and attributes).
**Prevention:** Use an AST NodeVisitor to maintain state (like aliased modules) and recursively validate calls. Always block dunder attributes like __subclasses__ and __globals__ which are primary tools for escaping limited environments.
