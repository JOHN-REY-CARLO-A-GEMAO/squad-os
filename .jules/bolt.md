## 2025-05-14 - [Optimized Tool Call Logging]
**Learning:** Transitioning from a single JSON array to a JSON Lines (JSONL) format for logging turns an O(N) read-modify-write operation into an O(1) append-only operation. This is especially critical for long-running agent missions where the log file grows with every tool call.
**Action:** Use append-only formats (like JSONL or SQLite) for high-frequency event logging to avoid performance degradation as history grows.

## 2025-05-15 - [Database Indexing & UI Caching]
**Learning:** SQLite query performance on status-based lookups (e.g., `QUEUED` missions) degrades linearly with table size. Adding targeted compound indexes (like `status, id`) reduces lookup time from O(N) to O(log N), yielding >99% speedup on large datasets. Additionally, Streamlit's `@st.cache_data` is effective for reducing database pressure during aggressive auto-refresh cycles (e.g., every 5s), but requires serializable return types (tuples instead of `sqlite3.Row`).
**Action:** Always index frequently queried status/filter columns and apply short-TTL caching to dashboard data loaders.
