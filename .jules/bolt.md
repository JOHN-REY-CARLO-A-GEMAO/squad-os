## 2025-04-12 - Database Indexing for Mission and Task Lookups
**Learning:** SQLite query performance on `status` and `mission_id` fields degrades as the number of tasks increases. Indexes significantly improve lookup times, especially for specific IDs (~60% speedup on 100k rows).
**Action:** Always index foreign keys and frequently filtered status columns in relational databases to ensure scalability.

## 2025-04-12 - Database Initialization Sequencing
**Learning:** Running migrations or creating indexes before tables are fully defined causes "no such table" errors on fresh installations.
**Action:** Ensure all `CREATE TABLE` statements are committed or executed before attempting to modify the schema (migrations) or add indexes in the initialization flow.
