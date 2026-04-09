import asyncio
import aiosqlite
import time
import os

DB_PATH = "benchmark.db"

async def setup_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("""
            CREATE TABLE missions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal TEXT NOT NULL,
                status TEXT NOT NULL,
                uploaded_files TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mission_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                assigned_agent TEXT NOT NULL,
                status TEXT NOT NULL,
                input_data TEXT,
                output_data TEXT,
                error TEXT,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0.0,
                execution_ms INTEGER DEFAULT 0,
                retry_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insert 1000 missions, all COMPLETED
        print("Inserting 1,000 missions...")
        missions = [(f"Mission {i}", "COMPLETED") for i in range(1000)]
        await db.executemany("INSERT INTO missions (goal, status) VALUES (?, ?)", missions)

        # Insert 100,000 tasks, all COMPLETED
        print("Inserting 100,000 tasks...")
        for batch in range(10):
            tasks = []
            for i in range(10000):
                idx = batch * 10000 + i
                mission_id = (idx % 1000) + 1
                status = "COMPLETED"
                output_data = f"Result of task {idx}"
                tasks.append((mission_id, f"Task {idx}", "agent", status, output_data))

            await db.executemany(
                "INSERT INTO tasks (mission_id, description, assigned_agent, status, output_data) VALUES (?, ?, ?, ?, ?)",
                tasks
            )
        await db.commit()

async def benchmark(db):
    results = {}

    # Query 1: Mission Queue (Next queued mission)
    # This should be slow without index if there are many missions but none are QUEUED
    start_time = time.time()
    for _ in range(100):
        async with db.execute(
            "SELECT * FROM missions WHERE status = 'QUEUED' ORDER BY id ASC LIMIT 1"
        ) as cursor:
            await cursor.fetchone()
    results['mission_queue'] = (time.time() - start_time) * 1000

    # Query 2: Search Past Memory (Tasks with COMPLETED status and specific output)
    start_time = time.time()
    for i in range(10):
        search_query = f"%Result of task {90000 + i}%"
        async with db.execute(
            "SELECT assigned_agent, output_data, created_at FROM tasks "
            "WHERE status = 'COMPLETED' AND output_data LIKE ? "
            "ORDER BY id DESC LIMIT 5",
            (search_query,)
        ) as cursor:
            await cursor.fetchall()
    results['memory_search'] = (time.time() - start_time) * 1000

    # Query 3: Tasks for a specific mission
    start_time = time.time()
    for i in range(100):
        mission_id = i + 1
        async with db.execute(
            "SELECT * FROM tasks WHERE mission_id = ?", (mission_id,)
        ) as cursor:
            await cursor.fetchall()
    results['tasks_by_mission'] = (time.time() - start_time) * 1000

    return results

async def main():
    await setup_db()

    async with aiosqlite.connect(DB_PATH) as db:
        print("Running benchmark WITHOUT indexes...")
        res_no_index = await benchmark(db)
        print("Results Without Index:")
        for k, v in res_no_index.items():
            print(f"  {k}: {v:.2f}ms")

        print("\nApplying indexes...")
        await db.execute("CREATE INDEX idx_missions_status_id ON missions(status, id)")
        await db.execute("CREATE INDEX idx_tasks_status_id ON tasks(status, id DESC, mission_id)")
        await db.execute("CREATE INDEX idx_tasks_mission_id ON tasks(mission_id)")
        await db.commit()

        # Clear cache by closing and reopening? Or just run.

    async with aiosqlite.connect(DB_PATH) as db:
        print("Running benchmark WITH indexes...")
        res_with_index = await benchmark(db)
        print("Results With Index:")
        for k, v in res_with_index.items():
            print(f"  {k}: {v:.2f}ms")

    print("\n--- Performance Impact ---")
    for k in res_no_index:
        improvement = ((res_no_index[k] - res_with_index[k]) / res_no_index[k]) * 100
        print(f"{k}: {res_no_index[k]:.2f}ms -> {res_with_index[k]:.2f}ms ({improvement:.2f}% faster)")

    os.remove(DB_PATH)

if __name__ == "__main__":
    asyncio.run(main())
