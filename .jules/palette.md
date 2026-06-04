## 2026-05-27 - Standardizing Selection Components with st.pills
**Learning:** Streamlit's `st.pills` (introduced in v1.34.0) provides a superior UX for single-select lists compared to manual button grids. It handles overflow automatically, maintains consistent spacing, and has built-in accessibility for screen readers and keyboard navigation (tabbing).
**Action:** Always prefer `st.pills` or `st.segmented_control` for selection interfaces instead of loops that generate multiple `st.button` elements.

## 2026-06-04 - Safety Popovers for Destructive Actions
**Learning:** Using `st.popover` for "Delete" or "Uninstall" actions provides a non-intrusive yet effective confirmation layer. It prevents accidental clicks on mobile/high-latency environments while keeping the UI clean by hiding the confirmation button until needed. Adding `st.warning` inside the popover and using `type="primary"` for the confirmation button creates a clear visual hierarchy of risk.
**Action:** Wrap destructive action buttons in an `st.popover` with an explicit confirmation step and use `help` tooltips for improved accessibility.
