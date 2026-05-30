# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-05-30 - AST vs Regex for Python Code Validation
**Vulnerability:** Regex-based Python code validation was bypassed using simple string concatenation (e.g., `o = 'o' + 's'; __import__(o)`) and aliasing (e.g., `import os as o; o.system('ls')`).
**Learning:** Regex is insufficient for validating dynamic languages like Python because it cannot track variable state or understand the semantic structure of the code (AST). Obfuscation and dynamic attribute access (`getattr`) are trivial to implement but hard for regex to catch.
**Prevention:** Use AST-based analysis to validate code. Track module aliases throughout the code and enforce strict rules on dynamic attribute access (e.g., requiring literal strings and checking against a blocklist). This provides a much deeper and more reliable security layer than pattern matching.
