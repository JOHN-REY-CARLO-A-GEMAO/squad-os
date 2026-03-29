## 2026-03-27 - [Path Traversal in File-Reading Tools]
**Vulnerability:** The `ReadFileTool` and `VisionAnalysisTool` were susceptible to path traversal attacks, allowing an agent (or a malicious user-provided mission) to access files outside the designated project workspace by using relative path sequences like `../../`.
**Learning:** Tools that interact with the filesystem often assume inputs are simple filenames, but when these inputs are concatenated with a base directory, they can resolve to locations outside the intended sandbox if not properly validated.
**Prevention:** Always use `os.path.realpath` to resolve paths and verify that the resolved path starts with the expected base directory before performing any filesystem operations. I implemented a reusable `is_safe_path` utility for this purpose.

## 2026-03-29 - [Local File Disclosure via browser_control]
**Vulnerability:** The `BrowserControlTool` allowed navigation to `file://` URLs, enabling an agent (or a malicious mission) to read local system files and sensitive information by taking screenshots of the rendered content.
**Learning:** Tools that wrap web browsers must explicitly restrict the allowed protocols (e.g., to `http://` and `https://`) to prevent them from being used for Server-Side Request Forgery (SSRF) or local file disclosure (LFD).
**Prevention:** Implement strict protocol whitelisting for all navigation actions in browser-based tools.
