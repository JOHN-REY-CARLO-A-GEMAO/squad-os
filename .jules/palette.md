## 2026-05-27 - Standardizing Selection Components with st.pills
**Learning:** Streamlit's `st.pills` (introduced in v1.34.0) provides a superior UX for single-select lists compared to manual button grids. It handles overflow automatically, maintains consistent spacing, and has built-in accessibility for screen readers and keyboard navigation (tabbing).
**Action:** Always prefer `st.pills` or `st.segmented_control` for selection interfaces instead of loops that generate multiple `st.button` elements.

## 2026-06-24 - Reliable Feedback with Session State and st.rerun
**Learning:** Calling  or  immediately before  is unreliable because the rerun terminates the current script execution, often preventing the feedback from being rendered or persisted.
**Action:** Use session state flags (e.g., `st.session_state.action_completed = True`) and a centralized notification block at the start of the UI section to display feedback after the rerun.

## 2026-06-24 - Reliable Feedback with Session State and st.rerun
**Learning:** Calling `st.toast` or `st.success` immediately before `st.rerun()` is unreliable because the rerun terminates the current script execution, often preventing the feedback from being rendered or persisted.
**Action:** Use session state flags (e.g., `st.session_state.action_completed = True`) and a centralized notification block at the start of the UI section to display feedback after the rerun.
