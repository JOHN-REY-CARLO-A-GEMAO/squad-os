## 2026-03-27 - [Path Traversal in File-Reading Tools]
**Vulnerability:** The `ReadFileTool` and `VisionAnalysisTool` were susceptible to path traversal attacks, allowing an agent (or a malicious user-provided mission) to access files outside the designated project workspace by using relative path sequences like `../../`.
**Learning:** Tools that interact with the filesystem often assume inputs are simple filenames, but when these inputs are concatenated with a base directory, they can resolve to locations outside the intended sandbox if not properly validated.
**Prevention:** Always use `os.path.realpath` to resolve paths and verify that the resolved path starts with the expected base directory before performing any filesystem operations. I implemented a reusable `is_safe_path` utility for this purpose.

## 2026-04-10 - [Local File Disclosure via Browser Control]
**Vulnerability:** `BrowserControlTool` allowed navigation to any URL, including `file://` protocols, which enabled Local File Disclosure (LFD) via screenshots of sensitive system files.
**Learning:** Browser-based tools inherit the local system's permissions for the `file://` protocol. Validating URLs must happen before passing them to the browser driver.
**Prevention:** Implement strict URL protocol whitelisting (e.g., only `http` and `https`) in tools that control browser navigation to prevent unintended local system access.
