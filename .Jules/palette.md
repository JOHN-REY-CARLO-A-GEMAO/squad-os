## 2026-03-27 - [Streamlit Dashboard Enhancements]
**Learning:** Adding visual cues for active states in sidebars and formatting raw timestamps significantly reduces cognitive load for users monitoring multi-agent missions.
**Action:** Always use distinct emojis or visual markers for selected items in lists and provide human-readable time formats instead of ISO strings.

## 2026-04-19 - [Toast Feedback & Log Readability]
**Learning:** Immediate visual confirmation (toasts) after destructive or async actions (like mission dispatching) significantly improves user confidence, especially when the page reruns. Formatting raw ISO logs into HH:MM:SS makes the dashboard feel like a real-time monitor.
**Action:** Use `st.session_state` flags to persist toast notifications across `st.rerun()` cycles and prioritize human-readable time formats in activity logs.
