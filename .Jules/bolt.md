## 2025-05-14 - Optimized project listing with os.scandir

**Learning:** Using `os.listdir()` followed by `os.path.isdir()` in a loop creates an O(2N) system call pattern (one to list, one per item to stat). `os.scandir()` provides `DirEntry` objects that already contain the file type information on most platforms, reducing system calls to O(1) for the entire directory scan. In SquadOS, this is particularly beneficial for the dashboard which auto-refreshes every 5 seconds.

**Action:** Prefer `os.scandir()` for directory traversal when filtering by file type or needing other metadata.
