## 2026-05-25 - Caching Global Stats in High-Frequency Dashboards
**Learning:** In dashboards with high-frequency auto-refreshes (e.g., every 5 seconds), global aggregation queries like `SUM()` or `COUNT()` on growing tables become a significant bottleneck. Streamlit's `@st.cache_data` is highly effective here, but must have a reasonable TTL to balance data freshness with performance.
**Action:** Always identify aggregate statistics that don't require real-time accuracy and apply `@st.cache_data` with a conservative TTL (e.g., 60s) to preserve database resources.

## 2026-05-27 - Caching Remote Registry Fetch
**Learning:** Functions that perform both local I/O and remote network requests (like `fetch_registry_packages`) are critical bottlenecks in high-frequency dashboards. Calling these every 5 seconds introduces cumulative latency (up to 300ms per call) and unnecessary network traffic.
**Action:** Apply `@st.cache_data` with a long TTL (e.g., 1h) to any function fetching static or semi-static data from external sources or disk within the main dashboard render loop.
