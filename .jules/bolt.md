## 2025-05-14 - [Optimized Tool Call Logging]
**Learning:** Transitioning from a single JSON array to a JSON Lines (JSONL) format for logging turns an O(N) read-modify-write operation into an O(1) append-only operation. This is especially critical for long-running agent missions where the log file grows with every tool call.
**Action:** Use append-only formats (like JSONL or SQLite) for high-frequency event logging to avoid performance degradation as history grows.
## 2026-04-05 - [Optimized SQLite Queries with Indexes]
**Learning:** Adding composite indexes on frequently queried columns (like `status` and `mission_id`) significantly reduces query latency. Composite index `(status, id)` is particularly effective for `LIMIT 1` queries that filter and sort simultaneously.
**Action:** Always index columns used in `WHERE` and `ORDER BY` clauses in SQLite, especially as the dataset grows beyond a few thousand rows.
