## 2026-03-27 - [Path Traversal in File-Reading Tools]
**Vulnerability:** The `ReadFileTool` and `VisionAnalysisTool` were susceptible to path traversal attacks, allowing an agent (or a malicious user-provided mission) to access files outside the designated project workspace by using relative path sequences like `../../`.
**Learning:** Tools that interact with the filesystem often assume inputs are simple filenames, but when these inputs are concatenated with a base directory, they can resolve to locations outside the intended sandbox if not properly validated.
**Prevention:** Always use `os.path.realpath` to resolve paths and verify that the resolved path starts with the expected base directory before performing any filesystem operations. I implemented a reusable `is_safe_path` utility for this purpose.

## 2026-03-28 - [Local File Disclosure via Browser Protocols]
**Vulnerability:** The `BrowserControlTool` allowed navigation to any URL protocol, including `file://`, which could be used to read sensitive files from the local filesystem and capture their content via screenshots.
**Learning:** Browser-based tools are often overlooked as potential vectors for local file access. Protocols like `file://`, `data:`, or `gopher://` can bypass traditional filesystem sandboxing if the browser process has access to those files.
**Prevention:** Restrict allowed URL protocols in browser tools to a safe whitelist (e.g., `http://` and `https://`) unless local file access is explicitly required and sandboxed.
