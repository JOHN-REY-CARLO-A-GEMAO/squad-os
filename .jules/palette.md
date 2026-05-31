## 2026-05-27 - Standardizing Selection Components with st.pills
**Learning:** Streamlit's `st.pills` (introduced in v1.34.0) provides a superior UX for single-select lists compared to manual button grids. It handles overflow automatically, maintains consistent spacing, and has built-in accessibility for screen readers and keyboard navigation (tabbing).
**Action:** Always prefer `st.pills` or `st.segmented_control` for selection interfaces instead of loops that generate multiple `st.button` elements.
## 2026-05-27 - Preventing DuplicateWidgetID in Streamlit Loops
**Learning:** When using components like `st.popover` or `st.button` inside a loop (e.g., iterating over agent personas or packages), Streamlit requires a unique `key` argument for each instance to prevent `DuplicateWidgetID` errors.
**Action:** Always provide a unique `key` (e.g., `key=f'pop_del_{item_id}'`) when creating widgets within a loop.
