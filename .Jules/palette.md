## 2026-03-27 - [Streamlit Dashboard Enhancements]
**Learning:** Adding visual cues for active states in sidebars and formatting raw timestamps significantly reduces cognitive load for users monitoring multi-agent missions.
**Action:** Always use distinct emojis or visual markers for selected items in lists and provide human-readable time formats instead of ISO strings.

## 2026-04-24 - [Mission Submission Feedback]
**Learning:** Providing immediate visual confirmation (like a toast notification) after a background task is triggered (like dispatching a mission) drastically improves perceived responsiveness and reduces user anxiety about whether their action "took".
**Action:** Use `st.toast` for non-blocking success confirmations in Streamlit, managing state with `st.session_state` to survive reruns.
