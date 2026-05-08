## 2026-05-08 - Optimized Directory Listing and Database Lookups

**Learning:** Using `os.scandir()` instead of `os.listdir()` provides a ~6-8x speedup for directory listing in the SquadOS project structure by reducing system calls from O(2N) to O(N). Database indexes on `mission_id` and `status` provide massive speedups (up to 80x+) for linked task lookups on large datasets.

**Action:** Prefer `os.scandir()` for any repeated directory traversal, especially in Streamlit apps with auto-refresh. Always index foreign keys and status columns used in filtering.
