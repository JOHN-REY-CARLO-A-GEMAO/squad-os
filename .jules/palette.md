## 2026-05-27 - Standardizing Selection Components with st.pills
**Learning:** Streamlit's `st.pills` (introduced in v1.34.0) provides a superior UX for single-select lists compared to manual button grids. It handles overflow automatically, maintains consistent spacing, and has built-in accessibility for screen readers and keyboard navigation (tabbing).
**Action:** Always prefer `st.pills` or `st.segmented_control` for selection interfaces instead of loops that generate multiple `st.button` elements.

## 2026-06-23 - Feedback Persistence and Safety Patterns
**Learning:** In Streamlit, feedback like `st.success` is often lost if followed by `st.rerun()`. Using session state-gated `st.toast` notifications at the start of the UI ensures the user sees confirmation after the page refreshes. Additionally, `st.popover` provides an elegant, non-intrusive way to implement "Confirm" patterns for destructive actions like deletion or uninstallation.
**Action:** Use session state flags + `st.toast` for post-rerun feedback. Implement destructive confirmations using `st.popover` with an `st.warning` and a primary-styled "Confirm" button.
