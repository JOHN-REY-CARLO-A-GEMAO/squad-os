## 2025-05-15 - Optimized Directory Traversal with os.scandir

**Learning:** Using os.listdir() followed by os.path.isdir() or os.path.isfile() in a loop creates an O(2N) system call pattern (one to list, one per item to stat). os.scandir() reduces this to O(N) by retrieving entry metadata during the initial directory traversal on most modern platforms.

**Action:** Prefer os.scandir() over os.listdir() when you need to filter entries by type (files vs directories) or access metadata (size, timestamps).
