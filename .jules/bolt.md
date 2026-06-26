## 2025-05-23 - Caching aggregate queries in Streamlit
**Learning:** In a Streamlit dashboard with auto-refresh enabled (e.g., every 5 seconds), even small database aggregate queries (SUM, COUNT) can become a bottleneck as the dataset grows (e.g., 100,000+ records).
**Action:** Always apply `@st.cache_data` with a reasonable TTL (e.g., 60s) to non-real-time global stats to preserve database resources and ensure smooth UI performance.

## 2026-06-26 - Lazy loading heavy columns in Streamlit
**Learning:** Fetching heavy TEXT or JSON columns (like conversation histories) in a frequently refreshing Streamlit dashboard (every 5 seconds) creates significant database I/O and parsing latency, especially as the number of missions grows.
**Action:** Use selective fetching (metadata only) for list views and implement on-demand "lazy loading" for full details only when an item is selected by the user.
