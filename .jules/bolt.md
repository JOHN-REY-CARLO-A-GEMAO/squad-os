# Bolt's Performance Journal

## 2024-05-14 - Directory Traversal Optimization
**Learning:** Using `os.scandir()` instead of `os.listdir()` followed by `os.path.isdir()` reduces the number of system calls from O(2N) to O(N) because `os.scandir()` retrieves file attributes (like whether it's a directory) during the initial directory listing.
**Action:** Always prefer `os.scandir()` for directory traversal when file metadata (type, size, etc.) is needed.
