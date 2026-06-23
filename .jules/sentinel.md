# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-05-24 - Windows Command Injection in open_app
**Vulnerability:** The `DesktopControlTool` used `shell=True` when calling `subprocess.Popen` on Windows in the `open_app` action, allowing for command injection if an attacker-controlled application name or path was provided.
**Learning:** Using `shell=True` on Windows is particularly risky as it passes the entire string to `cmd.exe`, which parses special characters like `&`, `|`, and `>`.
**Prevention:** Always use `shell=False` when executing external applications with user-provided strings. On Windows, if only a string is provided and `shell=False`, it is treated as the executable name/path and not parsed for shell operators.
