# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-05-24 - Windows Command Injection in DesktopControlTool
**Vulnerability:** `DesktopControlTool.open_app` used `shell=True` on Windows, allowing arbitrary command injection via shell operators like `&`.
**Learning:** Fixing command injection on Windows requires transitioning to `shell=False`. However, using `shlex.split(command, posix=False)` to parse Windows paths with spaces preserves quotes in the tokens. Passing these quoted tokens to `subprocess.Popen(shell=False)` leads to double-quoting and execution failure.
**Prevention:** Always manually strip quotes from tokens produced by `shlex.split(posix=False)` (e.g., `[p.strip('"') for p in parts]`) before passing them to `subprocess.Popen` on Windows when `shell=False` is used.
