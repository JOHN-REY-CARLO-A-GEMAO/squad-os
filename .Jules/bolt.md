## 2025-05-22 - Performance Optimization with `os.scandir`

**Learning:** Using `os.scandir` instead of `os.listdir` combined with `os.path.isdir` or `os.path.isfile` provides a significant performance gain (approx. 9x in benchmarks) for directory listing and filtering. This is because `os.scandir` yields `DirEntry` objects that include file attribute information without requiring additional system calls.

**Action:** Prefer `os.scandir` in high-frequency paths or when filtering files/directories by type, especially in auto-refreshing UI components like the Streamlit dashboard.
