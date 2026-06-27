## 2025-05-23 - Caching aggregate queries in Streamlit
**Learning:** In a Streamlit dashboard with auto-refresh enabled (e.g., every 5 seconds), even small database aggregate queries (SUM, COUNT) can become a bottleneck as the dataset grows (e.g., 100,000+ records).
**Action:** Always apply `@st.cache_data` with a reasonable TTL (e.g., 60s) to non-real-time global stats to preserve database resources and ensure smooth UI performance.

## 2026-06-27 - Lazy-loading heavy TEXT/JSON columns in Streamlit
**Learning:** Fetching heavy TEXT or JSON columns (like conversation history or workflow DAGs) in a frequently refreshing Streamlit dashboard (e.g., every 5 seconds) creates significant database I/O and parsing latency as the number of records grows.
**Action:** Use selective fetching for list views (selecting only metadata) and implement on-demand detail fetching for selected items to keep the auto-refresh cycle lean and responsive.
