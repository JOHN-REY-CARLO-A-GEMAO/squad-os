# Bolt Journal - Critical Performance Learnings

## 2025-05-14 - Directory Traversal Optimization
**Learning:** `os.scandir()` is significantly faster than `os.listdir()` followed by `os.path.isdir()` because it retrieves file attributes (like whether it's a directory) during the initial system call, reducing O(2N) syscalls to O(N).
**Action:** Use `os.scandir()` for any directory traversal or filtering logic in the dashboard to maintain responsiveness under high project counts.
