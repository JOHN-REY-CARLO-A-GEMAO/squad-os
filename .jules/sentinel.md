# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-06-11 - Windows Command Injection via shell=True
**Vulnerability:** Using `subprocess.Popen(app, shell=True)` in the `open_app` action allowed for command injection on Windows because the `app` string was executed via `cmd.exe`.
**Learning:** On Windows, `subprocess.Popen` with `shell=False` (default) can still accept a string. In this mode, it uses the `CreateProcess` API which does not interpret shell metacharacters like `&` or `|`, making it safe against shell injection while still handling paths with spaces.
**Prevention:** Avoid `shell=True` whenever possible, especially when dealing with user-controlled input. On Windows, prefer passing strings to `Popen` with `shell=False` for executing commands safely.
