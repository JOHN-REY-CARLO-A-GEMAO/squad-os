## 2026-03-27 - [Path Traversal in File-Reading Tools]
**Vulnerability:** The `ReadFileTool` and `VisionAnalysisTool` were susceptible to path traversal attacks, allowing an agent (or a malicious user-provided mission) to access files outside the designated project workspace by using relative path sequences like `../../`.
**Learning:** Tools that interact with the filesystem often assume inputs are simple filenames, but when these inputs are concatenated with a base directory, they can resolve to locations outside the intended sandbox if not properly validated.
**Prevention:** Always use `os.path.realpath` to resolve paths and verify that the resolved path starts with the expected base directory before performing any filesystem operations. I implemented a reusable `is_safe_path` utility for this purpose.

## 2026-04-02 - [SSRF and Local File Disclosure in BrowserControlTool]
**Vulnerability:** The `BrowserControlTool` allowed navigation to any URL, including those using the `file://` protocol. This could be exploited to read sensitive local files (like `/etc/passwd`) or perform Server-Side Request Forgery (SSRF) against internal services.
**Learning:** Browser-based tools are powerful and can access local system resources if not properly restricted. The `navigate` action is a common entry point for SSRF/LFD vulnerabilities in web-scraping or browser-automation features.
**Prevention:** Strictly validate URL protocols in browser-based tools. Only allow `http` and `https` unless there is a specific, well-justified need for other protocols. Implement protocol checking before calling `page.goto()`.
