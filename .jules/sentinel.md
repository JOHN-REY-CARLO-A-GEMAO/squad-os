## 2026-03-27 - [Path Traversal in File-Reading Tools]
**Vulnerability:** The `ReadFileTool` and `VisionAnalysisTool` were susceptible to path traversal attacks, allowing an agent (or a malicious user-provided mission) to access files outside the designated project workspace by using relative path sequences like `../../`.
**Learning:** Tools that interact with the filesystem often assume inputs are simple filenames, but when these inputs are concatenated with a base directory, they can resolve to locations outside the intended sandbox if not properly validated.
**Prevention:** Always use `os.path.realpath` to resolve paths and verify that the resolved path starts with the expected base directory before performing any filesystem operations. I implemented a reusable `is_safe_path` utility for this purpose.

## 2026-04-08 - [Path Traversal in Screenshot/Video Filenames]
**Vulnerability:** `BrowserControlTool` and `DesktopControlTool` were vulnerable to path traversal through the `description` parameter, which was used to construct filenames. An attacker could use `../../` in the description to write files outside the intended visual artifacts directory.
**Learning:** Even if a tool isn't explicitly reading/writing a user-provided "path", any string parameter used in filename construction is a potential path traversal vector if it's not sanitized.
**Prevention:** Use `os.path.basename()` on any user-provided string that will be used as a filename or part of a path. This strips any directory components and ensures the file is created in the intended directory.
