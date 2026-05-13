## 2025-05-13 - Initial Performance Audit
**Learning:** Found that `os.listdir()` combined with `os.path.isdir()` in `dashboard.py` creates N+1 system calls, which is a bottleneck when project count grows. Also, aggregate database queries in Streamlit refresh loops should be cached to prevent redundant DB load.
**Action:** Use `os.scandir()` for directory traversal and `st.cache_data` for expensive aggregate queries.
