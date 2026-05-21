## 2026-05-21 - Optimize directory traversal with os.scandir
**Learning:** Using `os.scandir()` provides a significant performance boost over `os.listdir()` when checking file attributes (like `is_dir()` or `is_file()`). In this codebase, `os.scandir()` was ~8x faster than `os.listdir()` + `os.path.isdir()` when scanning 1000 directories, because `scandir` retrieves file metadata in a single system call.
**Action:** Always prefer `os.scandir()` over `os.listdir()` when directory traversal requires filtering by file type or other metadata.
