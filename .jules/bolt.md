## 2025-05-14 - [Optimized Tool Call Logging]
**Learning:** Transitioning from a single JSON array to a JSON Lines (JSONL) format for logging turns an O(N) read-modify-write operation into an O(1) append-only operation. This is especially critical for long-running agent missions where the log file grows with every tool call.
**Action:** Use append-only formats (like JSONL or SQLite) for high-frequency event logging to avoid performance degradation as history grows.

## 2025-05-15 - [Optimized Artifact Committing]
**Learning:** Repeated directory traversals (like `os.walk`) in a loop create an O(M * N) bottleneck where M is the number of artifacts and N is the total file count. In a project with 10,000 files, committing 500 artifacts dropped from ~20+ seconds to ~0.15 seconds by using a single-pass mapping.
**Action:** When performing file system operations on a list of targets where location is uncertain, build a lookup table/mapping first to achieve O(N + M) performance.
