## 2026-05-27 - Standardizing Selection Components with st.pills
**Learning:** Streamlit's `st.pills` (introduced in v1.34.0) provides a superior UX for single-select lists compared to manual button grids. It handles overflow automatically, maintains consistent spacing, and has built-in accessibility for screen readers and keyboard navigation (tabbing).
**Action:** Always prefer `st.pills` or `st.segmented_control` for selection interfaces instead of loops that generate multiple `st.button` elements.

## 2026-05-28 - Safety Patterns for Destructive Actions
**Learning:** Destructive actions like deletion or uninstallation should never be a single click. Wrapping these buttons in an `st.popover` with a clear `st.warning` message and a primary-styled 'Confirm' button provides a lightweight but effective safety net that prevents accidental data loss while maintaining a clean UI.
**Action:** Use the "Popover Confirmation" pattern for any irreversible action. Combined with `st.session_state` and `st.toast`, it provides a complete and safe interaction loop.
