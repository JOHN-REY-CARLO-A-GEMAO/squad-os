## 2025-05-14 - [Optimized Tool Call Logging]
**Learning:** Transitioning from a single JSON array to a JSON Lines (JSONL) format for logging turns an O(N) read-modify-write operation into an O(1) append-only operation. This is especially critical for long-running agent missions where the log file grows with every tool call.
**Action:** Use append-only formats (like JSONL or SQLite) for high-frequency event logging to avoid performance degradation as history grows.

## 2026-04-08 - [Aggregated Query Optimization]
**Learning:** Database indexes are necessary for search stability, but application-level caching (Streamlit's `@st.cache_data`) provides the most dramatic latency reduction (99.9%+) for aggregated global statistics that don't need real-time precision.
**Action:** Implement short-TTL caching for expensive dashboard calculations and convert database results to primitive types (tuples) to ensure serializability.
