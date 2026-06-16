# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-06-16 - Windows Command Injection in DesktopControl
**Vulnerability:** Use of `shell=True` in `subprocess.Popen` when launching applications on Windows allowed for command chaining (e.g., using `&` or `|`) via the application path string.
**Learning:** On Windows, passing a string to `Popen` with `shell=True` executes it via `cmd.exe /c`, which interprets shell metacharacters. `shell=False` (the default) is much safer for simply launching an executable.
**Prevention:** Always use `shell=False` when executing commands with user-influenced input unless shell features are explicitly required and the input is strictly sanitized. For launching apps, `shell=False` is always preferred.
