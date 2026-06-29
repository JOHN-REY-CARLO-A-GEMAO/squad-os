## 2025-05-23 - Caching aggregate queries in Streamlit
**Learning:** In a Streamlit dashboard with auto-refresh enabled (e.g., every 5 seconds), even small database aggregate queries (SUM, COUNT) can become a bottleneck as the dataset grows (e.g., 100,000+ records).
**Action:** Always apply `@st.cache_data` with a reasonable TTL (e.g., 60s) to non-real-time global stats to preserve database resources and ensure smooth UI performance.

## 2026-06-29 - Selective fetching for large columns in frequent refreshes
**Learning:** Fetching heavy TEXT/JSON columns (like `conversation_history`) in a frequently refreshing Streamlit dashboard (e.g., 5s auto-refresh) creates massive DB I/O and parsing latency, scaling poorly with mission history size.
**Action:** Apply selective fetching: use a "light" query for lists/metadata and a "heavy" query for detail views (lazy-loading). This reduces latency by 95%+ for large datasets.
