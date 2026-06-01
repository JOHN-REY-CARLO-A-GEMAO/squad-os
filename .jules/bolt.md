## 2025-05-23 - Caching aggregate queries in Streamlit
**Learning:** In a Streamlit dashboard with auto-refresh enabled (e.g., every 5 seconds), even small database aggregate queries (SUM, COUNT) can become a bottleneck as the dataset grows (e.g., 100,000+ records).
**Action:** Always apply `@st.cache_data` with a reasonable TTL (e.g., 60s) to non-real-time global stats to preserve database resources and ensure smooth UI performance.

## 2026-06-01 - Eliminating heavy dependencies in auto-refreshing dashboards
**Learning:** In resource-constrained environments like Raspberry Pi 5, the import overhead of heavy libraries (e.g., `pandas` at ~0.6s-1.0s) can consume 20% of a 5-second auto-refresh budget. Streamlit's architecture re-runs the script frequently, making import time a direct contributor to UI latency.
**Action:** Favor native Python data structures (lists, dicts) and standard libraries over heavy dependencies like `pandas` for simple data fetching and display tasks in the dashboard.
