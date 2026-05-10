## 2025-05-10 - os.scandir for directory traversal
**Learning:** Using `os.scandir()` instead of `os.listdir()` + `os.path.isdir()` reduces system calls from O(2N) to O(N) by retrieving file type information during the initial iteration.
**Action:** Always prefer `os.scandir()` or `pathlib.Path.iterdir()` (which uses scandir internally) for high-frequency directory listings or when processing large numbers of files.

## 2025-05-10 - st.cache_data for periodic DB polling
**Learning:** Functions that perform expensive aggregate DB queries and are called during a Streamlit auto-refresh cycle (e.g., every 5s) should be cached with a TTL to reduce database pressure and UI latency.
**Action:** Apply `@st.cache_data(ttl=...)` to non-mutating DB read functions in Streamlit apps.
