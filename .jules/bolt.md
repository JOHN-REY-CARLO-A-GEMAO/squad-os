## 2025-05-14 - [Optimized Tool Call Logging]
**Learning:** Transitioning from a single JSON array to a JSON Lines (JSONL) format for logging turns an O(N) read-modify-write operation into an O(1) append-only operation. This is especially critical for long-running agent missions where the log file grows with every tool call.
**Action:** Use append-only formats (like JSONL or SQLite) for high-frequency event logging to avoid performance degradation as history grows.

## 2025-05-15 - [Efficient Filesystem Artifact Collection]
**Learning:** Performing `os.walk` inside a loop over a list of artifacts leads to O(M*N) complexity. Pre-calculating a file mapping (hash map of filename to paths) in a single walk reduces this to O(N+M), which scales much better for projects with many files or many artifacts to commit.
**Action:** Build look-up tables for filesystem metadata once and reuse them for repeated lookups within the same operation.
