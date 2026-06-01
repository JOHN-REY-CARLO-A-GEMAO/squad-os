# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-05-24 - Python Validation Bypass via Regex Limitations
**Vulnerability:** The Python code validation relied on regular expressions, which were easily bypassed using string concatenation (e.g., `'o' + 's'`) or dynamic attribute access (e.g., `getattr(obj, 'sub' + 'classes')`).
**Learning:** Regex is insufficient for validating code structure and semantics. Obfuscation techniques can trivialy bypass pattern-based detection.
**Prevention:** Use AST (Abstract Syntax Tree) analysis to validate code. This allows for reliable detection of imports, function calls, and attribute access regardless of string literal formatting. Strictly control `getattr` usage by ensuring it only uses literal strings that are checked against an allowlist/blocklist.
