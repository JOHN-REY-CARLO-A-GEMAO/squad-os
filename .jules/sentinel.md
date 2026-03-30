## 2026-03-27 - [Path Traversal in File-Reading Tools]
**Vulnerability:** The `ReadFileTool` and `VisionAnalysisTool` were susceptible to path traversal attacks, allowing an agent (or a malicious user-provided mission) to access files outside the designated project workspace by using relative path sequences like `../../`.
**Learning:** Tools that interact with the filesystem often assume inputs are simple filenames, but when these inputs are concatenated with a base directory, they can resolve to locations outside the intended sandbox if not properly validated.
**Prevention:** Always use `os.path.realpath` to resolve paths and verify that the resolved path starts with the expected base directory before performing any filesystem operations. I implemented a reusable `is_safe_path` utility for this purpose.

## 2026-03-30 - [SSRF and Local File Disclosure in Browser Tool]
**Vulnerability:** The `BrowserControlTool` allowed the `navigate` action to use any URL scheme, including `file://`. This enabled an agent to access sensitive local files (e.g., `/etc/hostname`) by navigating to them and then using screenshots or vision analysis to extract the content.
**Learning:** Web-browsing tools should be treated as a bridge to the external world, but their internal access must be strictly limited. Failing to restrict the URI scheme can expose the host filesystem or internal network services.
**Prevention:** Explicitly validate the URL scheme against an allowlist of permitted protocols (e.g., `['http', 'https']`) before performing navigation. Use `urllib.parse.urlparse` for robust parsing and ensure any surrounding whitespace is stripped from the input.
