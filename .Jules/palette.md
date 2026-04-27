## 2026-03-27 - [Streamlit Dashboard Enhancements]
**Learning:** Adding visual cues for active states in sidebars and formatting raw timestamps significantly reduces cognitive load for users monitoring multi-agent missions.
**Action:** Always use distinct emojis or visual markers for selected items in lists and provide human-readable time formats instead of ISO strings.

## 2026-04-27 - [Dashboard Professionalism & Feedback]
**Learning:** Standardizing empty states with `st.info` and relevant icons (🖼️, 📜, 🧠, ✅, 💬) creates a much more cohesive and professional feel than plain text. Additionally, using `st.toast` with `st.session_state` persistence is the ideal way to provide non-blocking success feedback in stateful Streamlit applications.
**Action:** Replace all "No [item] found" plain text with `st.info` and established iconography. Use `st.session_state` flags for post-rerun user feedback.
