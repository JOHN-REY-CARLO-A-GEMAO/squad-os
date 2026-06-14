# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2024-05-23 - Command Injection in DesktopControlTool
**Vulnerability:** `subprocess.Popen(app, shell=True)` on Windows allowed command injection via shell metacharacters (e.g., `&`) in the `app` parameter.
**Learning:** While `shell=True` is often used to launch GUI apps on Windows, it exposes the system to command injection if input is not sanitized.
**Prevention:** Use `shell=False` (default) for `subprocess.Popen` even when passing a string on Windows; it still launches the application but prevents shell interpretation of metacharacters like `&`.
