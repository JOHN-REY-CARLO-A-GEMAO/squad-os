# 🎨 Palette's Journal - UX & Accessibility Learnings

## 2025-05-15 - Standardizing Empty States with Micro-UX Patterns
**Learning:** In complex dashboards like SquadOS, plain text "empty states" (e.g., `st.write("No logs found")`) can be easily overlooked or mistaken for a loading glitch. Using `st.info` with themed icons provides a consistent visual anchor that clearly communicates "no data yet" as an expected state rather than an error.
**Action:** Always replace plain `st.write` empty states with `st.info` and a relevant emoji icon (e.g., 📜 for logs, 🖼️ for gallery) to improve scannability and provide a "delightful" micro-interaction.
