## 2025-05-23 - Caching aggregate queries in Streamlit
**Learning:** In a Streamlit dashboard with auto-refresh enabled (e.g., every 5 seconds), even small database aggregate queries (SUM, COUNT) can become a bottleneck as the dataset grows (e.g., 100,000+ records).
**Action:** Always apply `@st.cache_data` with a reasonable TTL (e.g., 60s) to non-real-time global stats to preserve database resources and ensure smooth UI performance.

## 2026-06-19 - Removing heavy shadow dependencies from Streamlit
**Learning:** `pandas` was used in the dashboard for simple SQLite queries despite not being in `requirements.txt`. In Streamlit, which re-executes on every interaction, the overhead of a heavy import like `pandas` (~0.7s) creates a noticeable lag compared to `sqlite3` (~0.01s).
**Action:** Avoid heavy libraries for simple data tasks in the dashboard. Use native Python collections and `sqlite3.Row` to maintain a snappy UI and minimal memory footprint.
