# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-05-29 - AST-based Python Validation vs Regex Bypass
**Vulnerability:** Regex-based Python code validation was easily bypassed using module aliasing (e.g., `import os as o`), `getattr()` with strings, and sensitive attribute access (e.g., `__subclasses__`).
**Learning:** Regex is insufficient for validating structured languages like Python where semantic equivalence can be achieved through many syntactic variations.
**Prevention:** Use `ast.parse()` and `ast.walk()` to perform semantic analysis of the code. Track module and function aliases, block forbidden built-ins explicitly, and restrict access to sensitive internal attributes. Block non-literal `getattr` to prevent dynamic runtime lookups.
