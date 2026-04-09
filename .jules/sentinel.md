## 2026-03-27 - [Path Traversal in File-Reading Tools]
**Vulnerability:** The `ReadFileTool` and `VisionAnalysisTool` were susceptible to path traversal attacks, allowing an agent (or a malicious user-provided mission) to access files outside the designated project workspace by using relative path sequences like `../../`.
**Learning:** Tools that interact with the filesystem often assume inputs are simple filenames, but when these inputs are concatenated with a base directory, they can resolve to locations outside the intended sandbox if not properly validated.
**Prevention:** Always use `os.path.realpath` to resolve paths and verify that the resolved path starts with the expected base directory before performing any filesystem operations. I implemented a reusable `is_safe_path` utility for this purpose.

## 2026-04-09 - [SSRF and Local File Disclosure in BrowserControlTool]
**Vulnerability:** The `BrowserControlTool` allowed navigation to any URL, including `file://` schemes, which could be exploited to read local sensitive files (Local File Disclosure) or access internal network services (SSRF) that the host has access to.
**Learning:** Browser-based tools are powerful and can bridge the gap between the external web and the local filesystem if not restricted. Default browser configurations often allow `file://` access.
**Prevention:** Implement strict URL scheme validation. Restrict allowed protocols to a safe allow-list (e.g., `http` and `https`) before initiating navigation.
