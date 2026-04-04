## 2026-03-27 - [Streamlit Dashboard Enhancements]
**Learning:** Adding visual cues for active states in sidebars and formatting raw timestamps significantly reduces cognitive load for users monitoring multi-agent missions.
**Action:** Always use distinct emojis or visual markers for selected items in lists and provide human-readable time formats instead of ISO strings.

## 2025-05-15 - [Standardizing Empty States and Contextual Tooltips]
**Learning:** Using `st.info` with standardized icons for empty states (🖼️, 📜, 🧠, 📋) provides much clearer feedback than plain text, and sidebar tooltips provide essential project context without requiring a context switch.
**Action:** Use `st.info(icon="...")` for all feature-specific empty states and leverage `st.button(help="...")` to surface secondary metadata in navigation components.
