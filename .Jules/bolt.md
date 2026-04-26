# Bolt Journal - Performance Optimizations

## 2026-04-26 - Optimized Database Performance with Targeted Indexes
**Learning:** Database queries on mission and task status, as well as mission_id joins, become significant bottlenecks as the database grows (O(N) full table scans).
**Action:** Always implement indexes on frequently queried state columns (status) and foreign keys (mission_id) using a robust sequential migration system that handles both legacy upgrades and fresh installations safely.
