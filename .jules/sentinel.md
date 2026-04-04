## 2026-03-27 - [Path Traversal in File-Reading Tools]
**Vulnerability:** The `ReadFileTool` and `VisionAnalysisTool` were susceptible to path traversal attacks, allowing an agent (or a malicious user-provided mission) to access files outside the designated project workspace by using relative path sequences like `../../`.
**Learning:** Tools that interact with the filesystem often assume inputs are simple filenames, but when these inputs are concatenated with a base directory, they can resolve to locations outside the intended sandbox if not properly validated.
**Prevention:** Always use `os.path.realpath` to resolve paths and verify that the resolved path starts with the expected base directory before performing any filesystem operations. I implemented a reusable `is_safe_path` utility for this purpose.

## 2026-04-04 - [Local File Disclosure in Browser Tools]
**Vulnerability:** The `BrowserControlTool` allowed navigation to local files using the `file://` protocol, which could be exploited to capture screenshots of sensitive system files (e.g., `/etc/passwd`).
**Learning:** Browser-based tools can be used to bypass filesystem restrictions if they support non-HTTP protocols. Protocol validation is essential for any tool that accepts a URL as input.
**Prevention:** Restrict browser navigation to a whitelist of allowed protocols (e.g., `http` and `https`) using `urllib.parse.urlparse` to validate the scheme before proceeding with the navigation.
