## 2026-05-14 - [Directory Traversal Optimization]
**Learning:** Replacing `os.listdir()` + `os.path.isdir()` with `os.scandir()` reduces system calls from O(2N) to O(N) by leveraging cached directory entry attributes, resulting in a measurable performance gain (approx. 6.3x speedup for 1000 directories in this environment).
**Action:** Use `os.scandir()` for any logic that iterates through directories and checks for entry types (file/dir) or metadata.
