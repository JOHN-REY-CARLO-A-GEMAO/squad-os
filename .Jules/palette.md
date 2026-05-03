## 2026-03-27 - [Streamlit Dashboard Enhancements]
**Learning:** Adding visual cues for active states in sidebars and formatting raw timestamps significantly reduces cognitive load for users monitoring multi-agent missions.
**Action:** Always use distinct emojis or visual markers for selected items in lists and provide human-readable time formats instead of ISO strings.

## 2025-05-15 - [Standardized Feedback & Empty States]
**Learning:** Standardizing empty states with `st.info` and specific icons (🖼️, 📜, 🧠, ✅) across tabs provides a cohesive feel and reduces "broken UI" perception when no data is present.
**Action:** Use `st.spinner` for mission dispatching and `st.toast` for success confirmation to close the feedback loop for asynchronous agent tasks.
