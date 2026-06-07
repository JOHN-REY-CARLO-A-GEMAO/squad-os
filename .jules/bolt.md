## 2025-05-23 - Caching aggregate queries in Streamlit
**Learning:** In a Streamlit dashboard with auto-refresh enabled (e.g., every 5 seconds), even small database aggregate queries (SUM, COUNT) can become a bottleneck as the dataset grows (e.g., 100,000+ records).
**Action:** Always apply `@st.cache_data` with a reasonable TTL (e.g., 60s) to non-real-time global stats to preserve database resources and ensure smooth UI performance.

## 2026-06-07 - Removing pandas dependency for dashboard performance
**Learning:** Removing `pandas` from a Streamlit dashboard reduces import overhead by ~0.76s per execution (from 0.77s to 0.01s). In a resource-constrained environment like Raspberry Pi 5 with frequent auto-refreshes, this significantly improves UI responsiveness and reduces memory footprint.
**Action:** Use native `sqlite3` with `sqlite3.Row` factory for simple database queries in Streamlit apps to avoid the heavy overhead of `pandas`.
