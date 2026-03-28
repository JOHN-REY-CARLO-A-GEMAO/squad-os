# 🎨 Palette's Journal - SquadOS

---

## 2026-03-28 - Testing Clipboard Interactions in Playwright
**Learning:** Browser APIs like `navigator.clipboard` require explicit permission grants in headless testing environments.
**Action:** Always include `context.grant_permissions(["clipboard-read", "clipboard-write"])` when using Playwright to verify copy-to-clipboard functionality to avoid `NotAllowedError`.

---
