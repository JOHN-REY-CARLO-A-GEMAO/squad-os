# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-05-24 - Desktop Control Command Injection
**Vulnerability:** `DesktopControlTool.open_app` used `subprocess.Popen(app, shell=True)` on Windows. This allowed command injection if an attacker could control the `app` parameter (e.g., passing `"calc.exe & echo vulnerable"`).
**Learning:** `shell=True` is almost always a security risk when handling external input, especially on Windows where a single string can contain multiple commands separated by `&`.
**Prevention:** Avoid `shell=True` whenever possible. Use `shell=False` (the default) and pass arguments as a list, or if a string must be passed (like for `open_app` on Windows), ensure it's handled safely by the OS without shell interpretation.
