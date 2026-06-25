## 2026-05-27 - Standardizing Selection Components with st.pills
**Learning:** Streamlit's `st.pills` (introduced in v1.34.0) provides a superior UX for single-select lists compared to manual button grids. It handles overflow automatically, maintains consistent spacing, and has built-in accessibility for screen readers and keyboard navigation (tabbing).
**Action:** Always prefer `st.pills` or `st.segmented_control` for selection interfaces instead of loops that generate multiple `st.button` elements.

## 2026-06-25 - Safety Patterns for Destructive Actions
**Learning:** Destructive actions like deleting personas or uninstalling packages should never be single-click. Using an `st.popover` containing an `st.warning` and a primary-style confirm button provides a lightweight, accessible "speed bump" that prevents accidental data loss while remaining non-modal and low-friction.
**Action:** Always wrap destructive UI elements in a confirmation popover with a clear warning and a high-contrast confirm button.
