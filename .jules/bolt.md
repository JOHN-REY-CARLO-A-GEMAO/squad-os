## 2025-05-23 - Caching aggregate queries in Streamlit
**Learning:** In a Streamlit dashboard with auto-refresh enabled (e.g., every 5 seconds), even small database aggregate queries (SUM, COUNT) can become a bottleneck as the dataset grows (e.g., 100,000+ records).
**Action:** Always apply `@st.cache_data` with a reasonable TTL (e.g., 60s) to non-real-time global stats to preserve database resources and ensure smooth UI performance.

## 2025-05-30 - Eliminating heavy dependencies for auto-refreshing UI
**Learning:** Using heavy libraries like `pandas` just for basic SQLite row-to-dict conversion in a high-frequency (5s) auto-refreshing Streamlit dashboard adds unnecessary memory overhead (~50-100MB per instance) and slows down application startup.
**Action:** Prefer standard Python lists and `sqlite3.Row` for simple database operations in lightweight dashboards. This reduces the application's memory footprint and eliminates crashes when heavy dependencies are missing in the runtime environment.
