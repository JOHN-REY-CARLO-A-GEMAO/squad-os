## 2026-03-27 - [Streamlit Dashboard Enhancements]
**Learning:** Adding visual cues for active states in sidebars and formatting raw timestamps significantly reduces cognitive load for users monitoring multi-agent missions.
**Action:** Always use distinct emojis or visual markers for selected items in lists and provide human-readable time formats instead of ISO strings.

## 2024-03-27 - [Standardized Dashboard UX & Feedback]
**Learning:** Standardizing empty states with consistent iconography and providing immediate toast feedback for background operations like mission dispatching makes the interface feel more responsive and cohesive.
**Action:** Use `st.info` with relevant icons for empty states and `st.toast` for operation confirmations.
