## 2026-03-27 - [Streamlit Dashboard Enhancements]
**Learning:** Adding visual cues for active states in sidebars and formatting raw timestamps significantly reduces cognitive load for users monitoring multi-agent missions.
**Action:** Always use distinct emojis or visual markers for selected items in lists and provide human-readable time formats instead of ISO strings.

## 2026-03-28 - [Standardizing Empty States]
**Learning:** Replacing plain text with `st.info` components and standardized icons for empty states significantly improves the visual professionalism and "scannability" of the dashboard, making it clear when content is pending versus missing.
**Action:** Use `st.info` with consistent icons (🖼️, 📜, 🧠, 📋, 💬, 🚀, 📦) for all empty or pending content areas in Streamlit apps.
