## 2026-05-27 - Standardizing Selection Components with st.pills
**Learning:** Streamlit's `st.pills` (introduced in v1.34.0) provides a superior UX for single-select lists compared to manual button grids. It handles overflow automatically, maintains consistent spacing, and has built-in accessibility for screen readers and keyboard navigation (tabbing).
**Action:** Always prefer `st.pills` or `st.segmented_control` for selection interfaces instead of loops that generate multiple `st.button` elements.

## 2026-06-05 - Safe Destructive Actions with st.popover
**Learning:** For destructive actions like deleting data or uninstalling packages, using `st.popover` to wrap a "Confirm" button provides a non-intrusive but effective safety net. Adding an `st.warning` inside the popover clearly communicates the consequences of the action.
**Action:** Use an `st.popover` containing an `st.warning` and a primary-style 'Confirm' button for all destructive actions in the dashboard.
