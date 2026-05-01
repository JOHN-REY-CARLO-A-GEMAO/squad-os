## 2026-03-27 - [Streamlit Dashboard Enhancements]
**Learning:** Adding visual cues for active states in sidebars and formatting raw timestamps significantly reduces cognitive load for users monitoring multi-agent missions.
**Action:** Always use distinct emojis or visual markers for selected items in lists and provide human-readable time formats instead of ISO strings.

## 2026-05-01 - [Standardized UX Micro-patterns]
**Learning:** Standardizing empty states with meaningful icons and wrapping asynchronous actions in spinners with persistent toast feedback creates a professional, cohesive feel that builds user trust in the system's state.
**Action:** Use `st.info` with specific icons (🖼️, 📜, 🧠, ✅, 💬) for empty states and follow the `st.spinner` + `st.toast` pattern for all mission dispatch actions.
