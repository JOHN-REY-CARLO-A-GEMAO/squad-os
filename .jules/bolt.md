## 2025-05-23 - Caching aggregate queries in Streamlit
**Learning:** In a Streamlit dashboard with auto-refresh enabled (e.g., every 5 seconds), even small database aggregate queries (SUM, COUNT) can become a bottleneck as the dataset grows (e.g., 100,000+ records).
**Action:** Always apply `@st.cache_data` with a reasonable TTL (e.g., 60s) to non-real-time global stats to preserve database resources and ensure smooth UI performance.

## 2026-06-20 - Removing heavy dependencies from high-frequency refresh cycles
**Learning:** `pandas` has a significant import overhead (~0.7s) and high memory footprint (50MB+). In a Streamlit dashboard with a frequent auto-refresh (e.g., every 5 seconds), this overhead accumulates and reduces UI responsiveness.
**Action:** For simple database operations in Streamlit, prefer native `sqlite3` with `sqlite3.Row` over `pandas`. This eliminates the heavy dependency and keeps the refresh cycle lean.
