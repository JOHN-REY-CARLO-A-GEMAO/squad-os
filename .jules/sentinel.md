## 2026-03-27 - [Path Traversal in File-Reading Tools]
**Vulnerability:** The `ReadFileTool` and `VisionAnalysisTool` were susceptible to path traversal attacks, allowing an agent (or a malicious user-provided mission) to access files outside the designated project workspace by using relative path sequences like `../../`.
**Learning:** Tools that interact with the filesystem often assume inputs are simple filenames, but when these inputs are concatenated with a base directory, they can resolve to locations outside the intended sandbox if not properly validated.
**Prevention:** Always use `os.path.realpath` to resolve paths and verify that the resolved path starts with the expected base directory before performing any filesystem operations. I implemented a reusable `is_safe_path` utility for this purpose.

## 2026-04-07 - [SSRF and Local File Disclosure in BrowserControlTool]
**Vulnerability:** The `BrowserControlTool` allowed navigation to any URL, including `file://` schemes, which could be exploited to read sensitive local files (like `/etc/passwd`) via screenshots or recordings.
**Learning:** Browser-based tools are inherently powerful and can access local resources if not restricted. Navigation must be limited to safe protocols, and subsequent actions (like screenshots) should only be permitted on authorized pages.
**Prevention:** Implement strict URL scheme validation to permit only `http://` and `https://` protocols. Additionally, add state-based checks to ensure tools do not capture data from uninitialized or forbidden browser states.
