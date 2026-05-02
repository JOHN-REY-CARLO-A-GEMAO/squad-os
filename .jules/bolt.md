# Bolt's Performance Journal ⚡

## 2025-05-02 - [Optimizing Directory Traversal]
**Learning:** `os.listdir()` followed by `os.path.isdir()` in a loop creates an O(2N) system call pattern (one to list, one per item to stat). `os.scandir()` reduces this to O(N) by retrieving entry metadata during the initial directory crawl. In a benchmark with 1000 directories, `os.scandir()` was ~6x faster than the `os.listdir()` + `os.path.isdir()` approach.
**Action:** Replace `os.listdir()` and `os.path.isdir()` loops with `os.scandir()` when filtering for directories or file types in `dashboard.py`.
