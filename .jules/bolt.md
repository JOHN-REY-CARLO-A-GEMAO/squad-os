## 2025-05-23 - Caching aggregate queries in Streamlit
**Learning:** In a Streamlit dashboard with auto-refresh enabled (e.g., every 5 seconds), even small database aggregate queries (SUM, COUNT) can become a bottleneck as the dataset grows (e.g., 100,000+ records).
**Action:** Always apply `@st.cache_data` with a reasonable TTL (e.g., 60s) to non-real-time global stats to preserve database resources and ensure smooth UI performance.

## 2026-05-29 - Removing pandas dependency from UI refresh cycles
**Learning:** For Streamlit dashboards with high-frequency auto-refresh (e.g., 5s), using pandas to load simple SQLite result sets introduces unnecessary overhead. Converting results directly to lists of dictionaries is significantly more efficient and reduces the memory footprint per refresh.
**Action:** Use standard `sqlite3.Row` and list comprehensions instead of `pd.read_sql_query` for basic UI data fetching.
