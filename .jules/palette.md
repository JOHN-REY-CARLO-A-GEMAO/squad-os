## 2026-05-27 - Standardizing Selection Components with st.pills
**Learning:** Streamlit's `st.pills` (introduced in v1.34.0) provides a superior UX for single-select lists compared to manual button grids. It handles overflow automatically, maintains consistent spacing, and has built-in accessibility for screen readers and keyboard navigation (tabbing).
**Action:** Always prefer `st.pills` or `st.segmented_control` for selection interfaces instead of loops that generate multiple `st.button` elements.

## 2026-06-03 - Protecting Destructive Actions with st.popover
**Learning:** Streamlit applications often execute actions immediately upon button click. For destructive operations like "Delete" or "Uninstall", using `st.popover` to wrap a confirmation warning and a primary-style confirm button creates a lightweight, accessible "two-step" verification that prevents accidental user errors without navigating away.
**Action:** Use `st.popover` with a `st.warning` and a confirmation button for all destructive or high-consequence UI actions.
