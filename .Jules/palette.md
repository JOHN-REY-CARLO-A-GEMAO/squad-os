## 2026-03-27 - [Streamlit Dashboard Enhancements]
**Learning:** Adding visual cues for active states in sidebars and formatting raw timestamps significantly reduces cognitive load for users monitoring multi-agent missions.
**Action:** Always use distinct emojis or visual markers for selected items in lists and provide human-readable time formats instead of ISO strings.

## 2026-05-08 - [Dashboard Accessibility & Shortcuts]
**Learning:** Streamlit's `st.button` and `st.download_button` support a `shortcut` parameter (e.g., `shortcut="Esc"`) which automatically renders a hint on the button. Combined with `help` tooltips, this significantly improves power-user efficiency and accessibility for icon-heavy dashboards.
**Action:** Always provide keyboard shortcut hints for primary navigation actions and tooltips for buttons that lack descriptive text labels.
