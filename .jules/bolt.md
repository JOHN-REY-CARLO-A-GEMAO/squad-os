## 2025-05-14 - [Optimized Tool Call Logging]
**Learning:** Transitioning from a single JSON array to a JSON Lines (JSONL) format for logging turns an O(N) read-modify-write operation into an O(1) append-only operation. This is especially critical for long-running agent missions where the log file grows with every tool call.
**Action:** Use append-only formats (like JSONL or SQLite) for high-frequency event logging to avoid performance degradation as history grows.

## 2026-04-10 - [Targeted Database Indexing]
**Learning:** Missing indexes on frequently queried status and foreign key columns lead to O(N) full table scans, which degrade performance linearly as history grows. Adding targeted composite indexes (e.g., `(status, id)`) converts these to O(log N) or O(1) lookups, providing measurable speedups (up to 13x) for dashboard polling.
**Action:** Always index columns used in `WHERE` clauses, `JOIN` conditions, and `ORDER BY` statements in relational databases to protect 'happy path' latency.
