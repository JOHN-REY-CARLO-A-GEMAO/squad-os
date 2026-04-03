## 2026-03-27 - [Path Traversal in File-Reading Tools]
**Vulnerability:** The `ReadFileTool` and `VisionAnalysisTool` were susceptible to path traversal attacks, allowing an agent (or a malicious user-provided mission) to access files outside the designated project workspace by using relative path sequences like `../../`.
**Learning:** Tools that interact with the filesystem often assume inputs are simple filenames, but when these inputs are concatenated with a base directory, they can resolve to locations outside the intended sandbox if not properly validated.
**Prevention:** Always use `os.path.realpath` to resolve paths and verify that the resolved path starts with the expected base directory before performing any filesystem operations. I implemented a reusable `is_safe_path` utility for this purpose.

## 2026-04-03 - [Local File Disclosure via Browser Protocol]
**Vulnerability:** The `BrowserControlTool` was vulnerable to Local File Disclosure (LFD) and Server-Side Request Forgery (SSRF) because it allowed navigating to arbitrary URI schemes, including `file://`.
**Learning:** Browser-based tools can bypass filesystem sandbox restrictions if they are allowed to access the local filesystem via the `file://` protocol.
**Prevention:** Strictly validate and whitelist allowed URL protocols (e.g., `http` and `https`) for any browser navigation actions.
