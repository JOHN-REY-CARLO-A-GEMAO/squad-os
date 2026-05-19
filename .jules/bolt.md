## 2026-05-19 - os.scandir() optimization for directory traversal
**Learning:** Using `os.scandir()` instead of `os.listdir()` followed by `os.path.isdir()` (or `os.path.isfile()`) significantly reduces the number of system calls. `os.scandir()` returns `DirEntry` objects that already contain file attribute information from the initial kernel directory listing, resulting in a ~6x performance gain for large directories.
**Action:** Always prefer `os.scandir()` with a context manager for any directory traversal or filtering logic.

## 2026-05-19 - Caching aggregate database queries in Streamlit
**Learning:** High-frequency auto-refresh (e.g., 5s) in Streamlit can create a hidden bottleneck if global stats are recalculated via `SUM()` or `COUNT()` on every refresh. `@st.cache_data(ttl=60)` effectively mitigates this.
**Action:** Cache aggregate database queries that don't need real-time precision (seconds-level) to protect database performance.
