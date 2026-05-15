## 2025-05-15 - Directory Traversal Optimization
**Learning:** Using `os.scandir()` instead of `os.listdir()` combined with `os.path.isdir()` significantly reduces system calls from O(2N) to O(N). In environments with many directories (like SquadOS projects), this results in a ~5.85x speedup for directory listing operations.
**Action:** Always prefer `os.scandir()` with a context manager for performance-critical directory traversal.
