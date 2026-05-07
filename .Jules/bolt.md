# Bolt Performance Journal ⚡

## 2025-05-07 - Syscall overhead in directory traversal
**Learning:** Using `os.listdir()` followed by `os.path.isdir()` in a loop results in O(2N) system calls because each `isdir` check triggers a new `stat` call. `os.scandir()` yields `DirEntry` objects that cache file metadata, reducing the overhead to O(N).

**Action:** Prefer `os.scandir()` for directory listings where file types or metadata are needed, especially in high-frequency paths like the Streamlit dashboard auto-refresh.
