## 2024-04-28 - os.scandir vs os.listdir
**Learning:** Using `os.scandir()` instead of `os.listdir()` followed by `os.path.isdir()` provides a significant performance boost (~7.5x in benchmarks with 1000 items). This is because `os.scandir()` retrieves file type information (like directory status) from the operating system during the initial scan, avoiding redundant `stat()` system calls.
**Action:** Always prefer `os.scandir()` for directory listings where file metadata or types are needed.
