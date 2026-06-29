# Sentinel Security Journal

## 2026-05-23 - Terminal Validation Path Traversal Bypass
**Vulnerability:** Absolute paths starting with `/` were incorrectly treated as command flags on POSIX systems, bypassing `is_safe_path` validation. Additionally, path-based commands (e.g., `./script.sh` or `/bin/ls`) were not consistently validated against the workspace or trusted directories.
**Learning:** Heuristic-based token classification (e.g., "if it starts with / it is a flag") is dangerous when applied across different operating systems. POSIX absolute paths must always be treated as paths for security validation.
**Prevention:** Explicitly check the operating system before applying flag-detection heuristics. Ensure that *all* tokens that look like paths, including the command name itself, are validated using `is_safe_path` or restricted to a strict whitelist of trusted system locations.

## 2026-06-29 - Windows Popen Shell Injection
**Vulnerability:** Using `subprocess.Popen(app, shell=True)` on Windows allows command injection via shell operators like `&` and `|`.
**Learning:** Even if the input is intended to be a single "app" path, `shell=True` invokes the command processor which interprets special characters. Switching to `shell=False` requires passing a list of arguments. However, `shlex.split(posix=False)` on Windows preserves quotes in tokens, which can lead to double-quoting when `subprocess` converts the list back to a string.
**Prevention:** Always use `shell=False` and pass a list of arguments. When using `shlex.split` on Windows, manually strip the outer quotes from tokens before passing them to `Popen` to ensure the OS-level command line is constructed correctly.
