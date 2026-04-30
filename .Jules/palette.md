## 2026-03-27 - [Streamlit Dashboard Enhancements]
**Learning:** Adding visual cues for active states in sidebars and formatting raw timestamps significantly reduces cognitive load for users monitoring multi-agent missions.
**Action:** Always use distinct emojis or visual markers for selected items in lists and provide human-readable time formats instead of ISO strings.

## 2026-04-30 - [Standardized Dashboard UX Micro-patterns]
**Learning:** Streamlit `st.toast` requires a `st.session_state` flag to persist across the mandatory `st.rerun()` cycle used for form submissions. Standardizing empty states with `st.info` and context-specific icons significantly improves visual hierarchy and screen reader clarity.
**Action:** Always use `st.info(..., icon=...)` for empty states and implement state-based toasts for async feedback.
