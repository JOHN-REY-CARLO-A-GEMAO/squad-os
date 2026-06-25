# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-05-24 - Windows Command Injection in DesktopControlTool
**Vulnerability:** `DesktopControlTool.open_app` used `shell=True` when executing commands on Windows, allowing arbitrary command execution via shell metacharacters (e.g., `&`, `|`) in the `app` parameter.
**Learning:** `subprocess.Popen` with `shell=True` on Windows is extremely dangerous as it invokes `cmd.exe /c`, which interprets a wide range of command separators. Even parameters intended as application names can be used to pivot into full shell access.
**Prevention:** Always use `shell=False` for subprocess execution. For Windows, use `shlex.split(command, posix=False)` to safely tokenize the command string into an argument list that can be passed to `Popen`.
