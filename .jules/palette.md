## 2026-05-27 - Standardizing Selection Components with st.pills
**Learning:** Streamlit's `st.pills` (introduced in v1.34.0) provides a superior UX for single-select lists compared to manual button grids. It handles overflow automatically, maintains consistent spacing, and has built-in accessibility for screen readers and keyboard navigation (tabbing).
**Action:** Always prefer `st.pills` or `st.segmented_control` for selection interfaces instead of loops that generate multiple `st.button` elements.

## 2026-06-01 - Standardizing Safety Popovers for Destructive Actions
**Learning:** Destructive actions like 'Delete' or 'Uninstall' should always be behind a confirmation step to prevent accidental data loss. Using 'st.popover' with 'st.warning' and a primary-colored confirmation button is a clean, non-intrusive pattern that keeps the user in flow while providing a safety net.
**Action:** Use 'with st.popover("🗑️ label", use_container_width=True):' followed by 'st.warning("Are you sure?")' and a confirmation button for all destructive UI elements.
