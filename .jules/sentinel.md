# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-05-24 - Desktop Control Command Injection
**Vulnerability:** `DesktopControlTool.open_app` used `shell=True` on Windows with unsanitized user input, allowing arbitrary command execution. On POSIX systems, it lacked argument separators, potentially allowing argument injection.
**Learning:** `shell=True` should be avoided whenever possible. When using `shell=False` on Windows with a list of arguments, `shlex.split(posix=False)` preserves quotes which can lead to double-quoting by Python's `list2cmdline`.
**Prevention:** Always use `shell=False`. On Windows, strip quotes from tokens produced by `shlex.split(posix=False)` before passing to `Popen`. On POSIX, use `--` to separate the command/binary from user-provided paths or arguments.
