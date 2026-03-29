## 2025-05-14 - [Optimized Tool Call Logging]
**Learning:** Transitioning from a single JSON array to a JSON Lines (JSONL) format for logging turns an O(N) read-modify-write operation into an O(1) append-only operation. This is especially critical for long-running agent missions where the log file grows with every tool call.
**Action:** Use append-only formats (like JSONL or SQLite) for high-frequency event logging to avoid performance degradation as history grows.

## 2026-03-29 - [Optimized Project Commit Artifact Search]
**Learning:** Performing repeated `os.walk` calls (O(M*N)) for multiple artifacts during a project commit causes significant latency as the number of files (N) and artifacts (M) increases. Building a lazy-initialized filename-to-path mapping (O(N+M)) is much more efficient.
**Action:** Replace nested loops performing expensive I/O or filesystem operations with pre-computed mappings or lookups to achieve linear performance.
