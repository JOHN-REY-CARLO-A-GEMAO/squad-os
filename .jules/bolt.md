## 2025-05-23 - Caching aggregate queries in Streamlit
**Learning:** In a Streamlit dashboard with auto-refresh enabled (e.g., every 5 seconds), even small database aggregate queries (SUM, COUNT) can become a bottleneck as the dataset grows (e.g., 100,000+ records).
**Action:** Always apply `@st.cache_data` with a reasonable TTL (e.g., 60s) to non-real-time global stats to preserve database resources and ensure smooth UI performance.

## 2026-06-03 - Removing pandas dependency for Streamlit performance
**Learning:** Removing heavy dependencies like `pandas` from a Streamlit app can significantly reduce startup time and memory footprint, especially in resource-constrained environments like Raspberry Pi 5. Streamlit's auto-refresh cycle (e.g., 5 seconds) also benefits from lighter imports.
**Action:** Prefer direct `sqlite3` calls and standard Python collections (lists, dicts) for simple data tasks in Streamlit dashboards to keep them responsive and efficient.
