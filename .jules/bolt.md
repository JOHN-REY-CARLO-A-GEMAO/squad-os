## 2025-05-23 - Caching aggregate queries in Streamlit
**Learning:** In a Streamlit dashboard with auto-refresh enabled (e.g., every 5 seconds), even small database aggregate queries (SUM, COUNT) can become a bottleneck as the dataset grows (e.g., 100,000+ records).
**Action:** Always apply `@st.cache_data` with a reasonable TTL (e.g., 60s) to non-real-time global stats to preserve database resources and ensure smooth UI performance.

## 2026-05-31 - Removing pandas for lightweight data retrieval
**Learning:** Using `pandas.read_sql_query` for simple database fetching in a high-frequency (5s refresh) Streamlit dashboard introduces unnecessary memory overhead and latency. Standard `sqlite3` with `conn.row_factory = sqlite3.Row` provides identical dictionary-like access without the heavy library footprint.
**Action:** Always prefer standard `sqlite3` or `aiosqlite` for simple row-based data retrieval in the dashboard to maintain a lightweight MAS framework.
