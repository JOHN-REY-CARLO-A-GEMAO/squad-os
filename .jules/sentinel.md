# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-05-24 - Desktop Tool Command Injection on Windows
**Vulnerability:** `DesktopControlTool.open_app` used `subprocess.Popen(app, shell=True)` on Windows, allowing arbitrary command execution via shell metacharacters (e.g., `&`, `|`).
**Learning:** `shell=True` on Windows is particularly dangerous because it uses `cmd.exe` by default, which has a wide range of command chaining operators. Even for simple "open app" functionality, the shell interpretation can be exploited.
**Prevention:** Always use `shell=False` for executing external processes. Use `shlex.split(command, posix=False)` to safely parse command strings into argument lists on Windows, ensuring that arguments are passed directly to the executable without shell processing.
