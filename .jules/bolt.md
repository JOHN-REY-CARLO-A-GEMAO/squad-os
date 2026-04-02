## 2025-05-14 - [Optimized Tool Call Logging]
**Learning:** Transitioning from a single JSON array to a JSON Lines (JSONL) format for logging turns an O(N) read-modify-write operation into an O(1) append-only operation. This is especially critical for long-running agent missions where the log file grows with every tool call.
**Action:** Use append-only formats (like JSONL or SQLite) for high-frequency event logging to avoid performance degradation as history grows.

## 2026-04-02 - [Optimized Artifact Resolution in ProjectBranch]
**Learning:** Repeatedly calling `os.walk` in a loop (once per artifact) creates an $O(Artifacts \times Files)$ complexity bottleneck, which is heavily I/O bound. Mapping the directory structure into an in-memory dictionary once reduces this to $O(Artifacts + Files)$, yielding ~8.5x speedup for 50 artifacts in 5000 files.
**Action:** When performing multiple lookups or scans in a file tree, build an in-memory index/map first to avoid redundant disk traversals.
