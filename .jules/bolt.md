## 2025-05-14 - [Optimized Tool Call Logging]
**Learning:** Transitioning from a single JSON array to a JSON Lines (JSONL) format for logging turns an O(N) read-modify-write operation into an O(1) append-only operation. This is especially critical for long-running agent missions where the log file grows with every tool call.
**Action:** Use append-only formats (like JSONL or SQLite) for high-frequency event logging to avoid performance degradation as history grows.

## 2026-04-04 - [Optimized Project Commit Artifact Discovery]
**Learning:** Performing an `os.walk` for every artifact in a commit operation results in O(Artifacts * Files) complexity, which becomes a major bottleneck for large projects. Building an in-memory file mapping during a single `os.walk` reduces the complexity to O(Files + Artifacts).
**Action:** Always prefer building a cache or mapping during a single filesystem traversal if multiple subsequent lookups are required within the same operation.
