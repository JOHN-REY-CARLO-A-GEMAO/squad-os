## 2026-04-16 - SSRF and LFD via Browser Control
**Vulnerability:** The `BrowserControlTool` allowed navigation to any URL, including `file://` and other non-web protocols, enabling Local File Disclosure (LFD) and potential Server-Side Request Forgery (SSRF).
**Learning:** Tools that wrap browser automation must strictly validate URL schemes to prevent access to the local filesystem or internal network services that the host might have access to.
**Prevention:** Implement a whitelist of allowed protocols (e.g., `http`, `https`) for any tool that accepts a URL for navigation or data fetching.
