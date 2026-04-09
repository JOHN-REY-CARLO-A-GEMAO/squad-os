## 2025-05-14 - [Optimized Tool Call Logging]
**Learning:** Transitioning from a single JSON array to a JSON Lines (JSONL) format for logging turns an O(N) read-modify-write operation into an O(1) append-only operation. This is especially critical for long-running agent missions where the log file grows with every tool call.
**Action:** Use append-only formats (like JSONL or SQLite) for high-frequency event logging to avoid performance degradation as history grows.

## 2026-04-09 - [Database Indexing for Scaling]
**Learning:** Without indexes, SQLite queries on status-based queues and foreign key joins become O(N) scans. Adding targeted multi-column indexes (e.g., `(status, id DESC)`) reduces query latency by >80% as the database scales to 100k+ tasks.
**Action:** Always index columns used in `WHERE` and `ORDER BY` clauses for core transactional tables.
