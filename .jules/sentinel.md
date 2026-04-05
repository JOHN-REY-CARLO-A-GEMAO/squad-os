## 2026-03-27 - [Path Traversal in File-Reading Tools]
**Vulnerability:** The `ReadFileTool` and `VisionAnalysisTool` were susceptible to path traversal attacks, allowing an agent (or a malicious user-provided mission) to access files outside the designated project workspace by using relative path sequences like `../../`.
**Learning:** Tools that interact with the filesystem often assume inputs are simple filenames, but when these inputs are concatenated with a base directory, they can resolve to locations outside the intended sandbox if not properly validated.
**Prevention:** Always use `os.path.realpath` to resolve paths and verify that the resolved path starts with the expected base directory before performing any filesystem operations. I implemented a reusable `is_safe_path` utility for this purpose.

## 2026-04-05 - [SSRF/LFD in Browser Tools]
**Vulnerability:** Insufficient protocol validation in browser tools allowed access to unauthorized schemes.
**Learning:** Browser automation tools require strict protocol controls as they can access local resources and internal networks even in headless mode.
**Prevention:** Enforce a whitelist of permitted URL schemes (e.g., http/https) for all browser navigation actions.
