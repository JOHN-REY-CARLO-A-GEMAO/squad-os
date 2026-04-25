## 2026-03-27 - [Streamlit Dashboard Enhancements]
**Learning:** Adding visual cues for active states in sidebars and formatting raw timestamps significantly reduces cognitive load for users monitoring multi-agent missions.
**Action:** Always use distinct emojis or visual markers for selected items in lists and provide human-readable time formats instead of ISO strings.

## 2026-04-25 - [Accessibility and Feedback Patterns in Streamlit]
**Learning:** Standardizing empty states with `st.info` and descriptive icons (🖼️, 📜, 🧠, ✅) creates a more professional and predictable UI. Providing immediate feedback for async actions via `st.toast` reduces user uncertainty.
**Action:** Use `st.info(icon=...)` for empty states and `st.session_state` flags to trigger `st.toast` success messages across mandatory page reruns.
