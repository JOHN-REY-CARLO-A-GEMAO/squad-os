## 2026-03-27 - [Streamlit Dashboard Enhancements]
**Learning:** Adding visual cues for active states in sidebars and formatting raw timestamps significantly reduces cognitive load for users monitoring multi-agent missions.
**Action:** Always use distinct emojis or visual markers for selected items in lists and provide human-readable time formats instead of ISO strings.
## 2026-04-22 - [Streamlit v1.56.0 UI Refinement]
**Learning:** Modern Streamlit (v1.56.0) has deprecated `use_container_width` in favor of `width="stretch"`. Additionally, using `st.info` with semantic icons for empty states significantly improves the "empty room" feeling of a new project.
**Action:** Transition all `use_container_width` components to `width="stretch"` and prioritize `st.info` for better visual feedback in empty states.
