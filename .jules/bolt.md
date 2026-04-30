## 2025-04-30 - [O(2N) to O(N) Syscall Reduction in Directory Listing]
**Learning:** Using `os.listdir()` followed by `os.path.isdir()` in a loop creates an O(2N) system call pattern (one to list, one per item to stat). `os.scandir()` reduces this to O(1) metadata retrieval per entry on most platforms (O(N) total), which is significantly faster for large directories.
**Action:** Always prefer `os.scandir()` or `pathlib.Path.iterdir()` when both names and file types/attributes are needed.
