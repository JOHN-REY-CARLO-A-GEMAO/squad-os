## 2026-05-27 - Standardizing Selection Components with st.pills
**Learning:** Streamlit's `st.pills` (introduced in v1.34.0) provides a superior UX for single-select lists compared to manual button grids. It handles overflow automatically, maintains consistent spacing, and has built-in accessibility for screen readers and keyboard navigation (tabbing).
**Action:** Always prefer `st.pills` or `st.segmented_control` for selection interfaces instead of loops that generate multiple `st.button` elements.

## 2026-06-28 - Safety Patterns for Destructive Actions in Streamlit
**Learning:** Destructive actions (delete, uninstall) in a Streamlit dashboard should never be exposed as single-click buttons. Using `st.popover` with an `st.warning` message and a primary "Confirm" button creates a lightweight, accessible confirmation flow that prevents data loss without requiring complex modal management.
**Action:** Wrap all destructive or non-reversible UI actions in an `st.popover` confirmation dialog with clear warning text and a high-contrast confirmation button.
