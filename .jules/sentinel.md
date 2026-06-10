# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-06-10 - Python Code Validation Regex Bypass
**Vulnerability:** The previous regex-based Python code validation could be bypassed using string concatenation (e.g., `__import__('o'+'s')`) or attribute access (e.g., `getattr()`) to invoke forbidden modules or methods.
**Learning:** Regex is insufficient for validating dynamic languages like Python. AST (Abstract Syntax Tree) analysis is required to reliably detect dangerous patterns by tracking imports and aliases.
**Prevention:** Use `ast.NodeVisitor` to analyze Python code at the structural level. Maintain state about imported modules and aliases to catch dangerous calls even when the code is obfuscated.
