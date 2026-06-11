## 2025-05-23 - Caching aggregate queries in Streamlit
**Learning:** In a Streamlit dashboard with auto-refresh enabled (e.g., every 5 seconds), even small database aggregate queries (SUM, COUNT) can become a bottleneck as the dataset grows (e.g., 100,000+ records).
**Action:** Always apply `@st.cache_data` with a reasonable TTL (e.g., 60s) to non-real-time global stats to preserve database resources and ensure smooth UI performance.

## 2026-05-27 - Removing Pandas from Streamlit Dashboards
**Learning:** Removing `pandas` from a Streamlit dashboard reduces import overhead by ~0.8s per execution. This is critical for high-frequency (5s) auto-refresh cycles, especially on resource-constrained hardware.
**Action:** Replace `pd.read_sql_query` with native `sqlite3` queries using `conn.row_factory = sqlite3.Row` and return lists of dictionaries to maintain similar developer ergonomics without the heavy dependency.
