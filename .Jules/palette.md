## 2026-03-27 - [Streamlit Dashboard Enhancements]
**Learning:** Adding visual cues for active states in sidebars and formatting raw timestamps significantly reduces cognitive load for users monitoring multi-agent missions.
**Action:** Always use distinct emojis or visual markers for selected items in lists and provide human-readable time formats instead of ISO strings.

## 2026-04-17 - [Standardizing Dashboard UI Patterns]
**Learning:** Standardizing empty states with `st.info` and descriptive icons (🖼️, 📜, 🧠, ✅, 💬, 🚀, 📦) provides immediate context and a more professional feel than plain text. Keyboard accessibility is significantly improved by adding `shortcut="Esc"` to primary navigation buttons.
**Action:** Use `st.info` for all empty states with consistent iconography. Always implement keyboard shortcuts and tooltips for common navigation actions to improve accessibility and discoverability.
