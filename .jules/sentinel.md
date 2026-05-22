## 2026-04-13 - [SSRF/LFD and Path Traversal in Visual Tools]
**Vulnerability:** BrowserControlTool allowed navigation to `file://` URIs, enabling Local File Disclosure (LFD). Additionally, BrowserControlTool and DesktopControlTool allowed path traversal via the `description` parameter in screenshot/video actions.
**Learning:** Tools that accept URLs must be restricted to safe web protocols (`http`, `https`). User-provided strings used in filename construction must be sanitized using `os.path.basename()` to prevent directory traversal.
**Prevention:** Implement protocol allowlists for all URL-accepting tools and always sanitize filename inputs.
