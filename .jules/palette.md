## 2026-05-27 - Standardizing Selection Components with st.pills
**Learning:** Streamlit's `st.pills` (introduced in v1.34.0) provides a superior UX for single-select lists compared to manual button grids. It handles overflow automatically, maintains consistent spacing, and has built-in accessibility for screen readers and keyboard navigation (tabbing).
**Action:** Always prefer `st.pills` or `st.segmented_control` for selection interfaces instead of loops that generate multiple `st.button` elements.

## 2026-05-30 - Safety Popovers for Destructive Actions
**Learning:** For destructive UI actions like deletion or uninstallation in Streamlit, using `st.popover` provides a non-intrusive yet effective "speed bump". It keeps the UI clean while preventing accidental clicks better than a simple button.
**Action:** Use `st.popover` with an `st.warning` and a primary confirmation button for any irreversible user actions.
