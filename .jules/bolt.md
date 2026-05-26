## 2026-05-25 - Caching Global Stats in High-Frequency Dashboards
**Learning:** In dashboards with high-frequency auto-refreshes (e.g., every 5 seconds), global aggregation queries like `SUM()` or `COUNT()` on growing tables become a significant bottleneck. Streamlit's `@st.cache_data` is highly effective here, but must have a reasonable TTL to balance data freshness with performance.
**Action:** Always identify aggregate statistics that don't require real-time accuracy and apply `@st.cache_data` with a conservative TTL (e.g., 60s) to preserve database resources.
