# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-06-15 - Command Injection in DesktopControlTool via shell=True
**Vulnerability:** The `DesktopControlTool` on Windows used `subprocess.Popen(app, shell=True)`, which allowed arbitrary command execution if the `app` string contained shell metacharacters like `&` or `|`.
**Learning:** Using `shell=True` with user-provided or agent-generated strings is a classic security risk. Even when the intent is just to "open an app", the shell interpreter will parse the entire string.
**Prevention:** Always use `shell=False` (the default) and pass arguments as a list whenever possible. For Windows `open_app` specifically, passing the app path as a string with `shell=False` is sufficient and much safer.
