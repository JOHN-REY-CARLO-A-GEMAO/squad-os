## 2025-05-23 - Caching aggregate queries in Streamlit
**Learning:** In a Streamlit dashboard with auto-refresh enabled (e.g., every 5 seconds), even small database aggregate queries (SUM, COUNT) can become a bottleneck as the dataset grows (e.g., 100,000+ records).
**Action:** Always apply `@st.cache_data` with a reasonable TTL (e.g., 60s) to non-real-time global stats to preserve database resources and ensure smooth UI performance.
## 2026-06-21 - Removing pandas dependency from dashboard
**Learning:** The `pandas` library has a high import overhead (~0.77s) and significant memory footprint (~50-100MB+). In a Streamlit dashboard with a 5-second auto-refresh cycle, this overhead is incurred during every full script rerun if the dependency is used. Replacing it with native `sqlite3` and Python list/dict operations significantly improves UI responsiveness and reduces resource usage.
**Action:** Always prefer native Python collections and direct `sqlite3` calls over heavy data analysis libraries like `pandas` for simple CRUD operations in resource-constrained or high-frequency refresh environments.
