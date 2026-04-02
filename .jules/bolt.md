## 2025-05-14 - [Optimized Tool Call Logging]
**Learning:** Transitioning from a single JSON array to a JSON Lines (JSONL) format for logging turns an O(N) read-modify-write operation into an O(1) append-only operation. This is especially critical for long-running agent missions where the log file grows with every tool call.
**Action:** Use append-only formats (like JSONL or SQLite) for high-frequency event logging to avoid performance degradation as history grows.

## 2025-05-15 - [Database Performance Indexes]
**Learning:** Adding composite and targeted indexes to SQLite tables (`missions`, `tasks`) drastically reduces query latency for mission queue management and historical task searches. Measured improvements showed ~4x faster mission lookups and ~3.4x faster memory searches on a 1000-record dataset.
**Action:** Always index columns used in `WHERE`, `ORDER BY`, and `JOIN` clauses in relational databases to maintain O(log N) lookup performance as the dataset scales.
