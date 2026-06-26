## 2026-05-27 - Standardizing Selection Components with st.pills
**Learning:** Streamlit's `st.pills` (introduced in v1.34.0) provides a superior UX for single-select lists compared to manual button grids. It handles overflow automatically, maintains consistent spacing, and has built-in accessibility for screen readers and keyboard navigation (tabbing).
**Action:** Always prefer `st.pills` or `st.segmented_control` for selection interfaces instead of loops that generate multiple `st.button` elements.

## 2026-05-28 - Safety Confirmations and Persistent Feedback
**Learning:** Destructive actions (deletion, uninstallation) must be gated by a confirmation step to prevent accidental data loss. Using `st.popover` allows for an in-place confirmation flow that is less disruptive than a full-page modal or navigation. Furthermore, since Streamlit reruns on interaction, using `st.session_state` to trigger `st.toast` ensures that feedback is delivered reliably after the state change.
**Action:** Implement destructive actions using an `st.popover` containing an `st.warning` and a primary-style 'Confirm' button. Use session-state flags (e.g., `st.session_state.action_completed`) to trigger notifications at the top of the UI section.
