## 2026-05-27 - Standardizing Selection Components with st.pills
**Learning:** Streamlit's `st.pills` (introduced in v1.34.0) provides a superior UX for single-select lists compared to manual button grids. It handles overflow automatically, maintains consistent spacing, and has built-in accessibility for screen readers and keyboard navigation (tabbing).
**Action:** Always prefer `st.pills` or `st.segmented_control` for selection interfaces instead of loops that generate multiple `st.button` elements.

## 2026-05-29 - Safeguarding Destructive Actions with Popovers
**Learning:** For destructive actions like deletion or uninstallation, using `st.popover` provides a non-intrusive yet effective confirmation layer. It prevents accidental clicks while keeping the main UI clean compared to modal dialogs or "are you sure" text flags.
**Action:** Use `st.popover` with an internal `st.warning` and a primary-colored "Confirm" button for all destructive UI operations.
