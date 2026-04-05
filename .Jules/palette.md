## 2026-03-27 - [Streamlit Dashboard Enhancements]
**Learning:** Adding visual cues for active states in sidebars and formatting raw timestamps significantly reduces cognitive load for users monitoring multi-agent missions.
**Action:** Always use distinct emojis or visual markers for selected items in lists and provide human-readable time formats instead of ISO strings.

## 2026-04-03 - [Standardizing Empty States]
**Learning:** Plain text empty states often feel like "broken" or "missing" data. Using `st.info` with themed icons transforms these moments into helpful status updates that maintain the visual rhythm of the dashboard.
**Action:** Replace plain text empty states with `st.info` and an icon that matches the tab's context (e.g., 🖼️ for Gallery, 📜 for Logs).
