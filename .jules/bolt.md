## 2025-05-23 - Caching aggregate queries in Streamlit
**Learning:** In a Streamlit dashboard with auto-refresh enabled (e.g., every 5 seconds), even small database aggregate queries (SUM, COUNT) can become a bottleneck as the dataset grows (e.g., 100,000+ records).
**Action:** Always apply `@st.cache_data` with a reasonable TTL (e.g., 60s) to non-real-time global stats to preserve database resources and ensure smooth UI performance.

## 2026-06-02 - Removing heavy dependencies from refresh-loop scripts
**Learning:** For scripts that run in a frequent loop (like a Streamlit dashboard with 5s auto-refresh), the overhead of importing heavy libraries like `pandas` (0.6s-1.0s) can consume a large fraction of the available CPU time on hardware like Raspberry Pi 5.
**Action:** Use native Python data structures (lists/dicts) and standard library alternatives (like `sqlite3.Row` instead of `pd.read_sql`) to keep the refresh cycle lean and responsive.
