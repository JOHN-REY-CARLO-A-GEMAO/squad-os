## 2026-04-21 - [CRITICAL] Shell Operator Bypass in TerminalTool
**Vulnerability:** The `TerminalTool` failed to validate sub-commands when shell operators like `;`, `&&`, `||`, `|`, or `&` were used. An attacker could execute arbitrary unauthorized commands by chaining them with an allowed command.
**Learning:** `shlex.split()` or simple string splitting is insufficient for validating complex shell commands because it doesn't recognize shell-specific punctuation that separates distinct commands.
**Prevention:** Use `shlex.shlex(punctuation_chars=True)` to properly tokenize command strings and ensure every token that follows a shell operator is validated against the allowlist.

## 2026-04-21 - [CRITICAL] SSRF and Local File Disclosure in BrowserControlTool
**Vulnerability:** The `BrowserControlTool` allowed navigation to `file://` URLs, enabling the browser to read and screenshot sensitive local files (e.g., `/etc/passwd`).
**Learning:** Headless browsers can be used to access the local file system unless explicitly restricted by protocol allowlists.
**Prevention:** Explicitly validate the URL scheme and restrict it to a safe allowlist (e.g., `['http', 'https']`) before initiating navigation.
