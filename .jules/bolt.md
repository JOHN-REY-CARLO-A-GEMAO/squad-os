## 2025-05-23 - Caching aggregate queries in Streamlit
**Learning:** In a Streamlit dashboard with auto-refresh enabled (e.g., every 5 seconds), even small database aggregate queries (SUM, COUNT) can become a bottleneck as the dataset grows (e.g., 100,000+ records).
**Action:** Always apply `@st.cache_data` with a reasonable TTL (e.g., 60s) to non-real-time global stats to preserve database resources and ensure smooth UI performance.
