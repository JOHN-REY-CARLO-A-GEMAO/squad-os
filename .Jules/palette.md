## 2026-03-27 - [Streamlit Dashboard Enhancements]
**Learning:** Adding visual cues for active states in sidebars and formatting raw timestamps significantly reduces cognitive load for users monitoring multi-agent missions.
**Action:** Always use distinct emojis or visual markers for selected items in lists and provide human-readable time formats instead of ISO strings.

## 2026-04-09 - [Enhanced Dashboard Interactivity & Accessibility]
**Learning:** Using `st.spinner` and `st.toast` provides immediate, reassuring feedback for long-running agent tasks. Native `st.metric` formatting and borders improve the professional feel of the command center.
**Action:** Always include feedback loops (spinners/toasts) for async actions and use tooltips (`help` parameter) for all icon-heavy interactive elements.
