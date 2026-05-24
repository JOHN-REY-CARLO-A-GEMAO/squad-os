## 2026-05-24 - [Dashboard] Caching Global Stats
**Learning:** Streamlit's @st.cache_data requires return values to be pickle-serializable. Database cursor results (like sqlite3.Row) must be explicitly converted to standard Python types (e.g., list or tuple) before being returned from a cached function.
**Action:** Always ensure database results are converted to standard types when using @st.cache_data.
