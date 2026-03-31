## 2025-05-14 - [Optimized Tool Call Logging]
**Learning:** Transitioning from a single JSON array to a JSON Lines (JSONL) format for logging turns an O(N) read-modify-write operation into an O(1) append-only operation. This is especially critical for long-running agent missions where the log file grows with every tool call.
**Action:** Use append-only formats (like JSONL or SQLite) for high-frequency event logging to avoid performance degradation as history grows.

## 2025-05-15 - [Database and UI Caching Optimization]
**Learning:** SQLite performance in SquadOS was bottlenecked by table scans as mission history grew. Adding specific composite indexes reduced queue lookup times by ~6.5x. Furthermore, Streamlit's `st_autorefresh` every 5 seconds caused redundant database queries; implementing `@st.cache_data(ttl=5)` significantly reduced database pressure while maintaining real-time feel. Note: `sqlite3.Row` objects are not serializable by Streamlit's cache and must be converted to primitives (like tuples).
**Action:** Always add indexes to frequently queried columns (status, mission_id) and use short-TTL caching for high-frequency dashboard updates.
