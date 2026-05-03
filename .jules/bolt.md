## 2026-05-03 - os.scandir() vs os.listdir()
**Learning:** Using `os.scandir()` instead of `os.listdir()` followed by `os.path.isdir()` or `os.path.isfile()` significantly reduces system calls from O(2N) to O(N). In environments with many directories or files, this can lead to a 7-8x performance improvement for directory listing operations.
**Action:** Always prefer `os.scandir()` for directory traversal when file attributes (type, size, etc.) are needed alongside the names.
