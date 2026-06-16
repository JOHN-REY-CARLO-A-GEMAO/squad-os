## 2025-05-23 - Caching aggregate queries in Streamlit
**Learning:** In a Streamlit dashboard with auto-refresh enabled (e.g., every 5 seconds), even small database aggregate queries (SUM, COUNT) can become a bottleneck as the dataset grows (e.g., 100,000+ records).
**Action:** Always apply `@st.cache_data` with a reasonable TTL (e.g., 60s) to non-real-time global stats to preserve database resources and ensure smooth UI performance.

## 2025-05-24 - Removing heavyweight dependencies from auto-refreshing UI
**Learning:** Profiling showed that `pandas` import overhead (~0.77s) and its memory footprint (50-100MB+) were unnecessary for simple dashboard data fetching. In a UI with a 5-second auto-refresh cycle, every millisecond of script execution time matters for responsiveness.
**Action:** Replace `pandas` with native `sqlite3` and Python data structures (lists/dicts) for simple CRUD and dashboard views. This improves cold-start time and significantly reduces memory usage without sacrificing readability.
