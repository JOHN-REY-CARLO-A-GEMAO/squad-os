# Bolt's Journal - Performance Optimizations

This journal records critical learnings from performance optimizations in SquadOS.

## 2025-05-14 - Journal Initialized
**Learning:** Initializing the Bolt journal to track performance-obsessed improvements.
**Action:** Always measure before and after optimization.

## 2026-04-21 - Optimized directory listing with os.scandir
**Learning:** `os.listdir` combined with `os.path.isdir` or `os.path.isfile` results in redundant system calls because `os.listdir` only returns names, forcing subsequent `stat` calls to determine file types. In a Streamlit dashboard with a 5-second auto-refresh, these redundant calls accumulate, especially as the number of projects or visual artifacts grows. `os.scandir` returns iterator of `DirEntry` objects which contain file type information from the initial directory scan on most platforms.
**Action:** Prefer `os.scandir` over `os.listdir` when filtering by file type (is_dir/is_file) during directory traversal. Benchmark showed ~6.1x performance improvement for 1000 directories.
