## 2025-04-19 - Use os.scandir for directory listing with metadata checks
**Learning:** Using `os.scandir()` instead of `os.listdir()` combined with `os.path.isdir()` or `os.path.isfile()` provides a significant performance gain (~6x in benchmarks) because `os.scandir()` retrieves file attributes along with the filename in a single system call.
**Action:** Always prefer `os.scandir()` over `os.listdir()` when you need to filter by file type or access other metadata during directory traversal.
