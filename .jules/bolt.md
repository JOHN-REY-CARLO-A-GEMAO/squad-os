## 2025-05-14 - [Optimized Tool Call Logging]
**Learning:** Transitioning from a single JSON array to a JSON Lines (JSONL) format for logging turns an O(N) read-modify-write operation into an O(1) append-only operation. This is especially critical for long-running agent missions where the log file grows with every tool call.
**Action:** Use append-only formats (like JSONL or SQLite) for high-frequency event logging to avoid performance degradation as history grows.

## 2025-05-14 - [O(N+M) Artifact Commitment]
**Learning:** Nested `os.walk` calls inside a loop result in O(Artifacts * TotalFiles) complexity. For projects with thousands of files, this causes significant UI lag during the commit phase. However, pre-building a full file map can introduce overhead for the "happy path" (exact matches).
**Action:** Use a two-phase approach for artifact commitment: 1) Fast-path O(M) check for exact matches using `os.path.exists`. 2) Only perform a single project walk O(N) if any artifacts are missing, searching for multiple targets in one pass.
