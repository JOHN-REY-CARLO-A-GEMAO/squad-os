## 2026-03-27 - [Path Traversal in File-Reading Tools]
**Vulnerability:** The `ReadFileTool` and `VisionAnalysisTool` were susceptible to path traversal attacks, allowing an agent (or a malicious user-provided mission) to access files outside the designated project workspace by using relative path sequences like `../../`.
**Learning:** Tools that interact with the filesystem often assume inputs are simple filenames, but when these inputs are concatenated with a base directory, they can resolve to locations outside the intended sandbox if not properly validated.
**Prevention:** Always use `os.path.realpath` to resolve paths and verify that the resolved path starts with the expected base directory before performing any filesystem operations. I implemented a reusable `is_safe_path` utility for this purpose.

## 2026-04-06 - [SSRF and Local File Disclosure in BrowserControlTool]
**Vulnerability:** The `BrowserControlTool` allowed navigation to any URL protocol supported by the underlying browser engine (Playwright), including `file://`. This enabled agents to read local system files or access internal network resources (SSRF) by simply navigating to them and capturing screenshots.
**Learning:** Browser-based tools are powerful because they support many protocols out-of-the-box, but this versatility is a security risk in a sandboxed environment. Navigating to `file:///etc/passwd` is as easy as navigating to `https://google.com`.
**Prevention:** Implement strict protocol whitelisting for all browser navigation actions. Use `urllib.parse.urlparse` to extract the scheme and only permit `http` and `https`.
