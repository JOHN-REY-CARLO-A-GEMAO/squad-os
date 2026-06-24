# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-05-24 - Windows Command Injection in DesktopControlTool
**Vulnerability:** `DesktopControlTool.open_app` used `shell=True` on Windows with raw user input, allowing command chaining (e.g., `app & malicious_cmd`).
**Learning:** Windows `subprocess.Popen` with `shell=True` is particularly dangerous because it uses `cmd.exe`, which has different parsing rules than POSIX shells. `shlex.split(..., posix=False)` is necessary to correctly tokenize Windows commands for `shell=False` without stripping path backslashes.
**Prevention:** Never use `shell=True` with user-supplied input. Always tokenize command strings using `shlex` with platform-appropriate settings and execute with `shell=False`.
