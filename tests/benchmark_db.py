import asyncio
import aiosqlite
import time
import os

DB_PATH = "shared_memory.db"

async def setup_data():
    async with aiosqlite.connect(DB_PATH) as db:
        # Clear existing data for a clean benchmark
        await db.execute("DELETE FROM tasks")
        await db.execute("DELETE FROM missions")
        await db.commit()

        print("Inserting 10,000 missions...")
        missions = [
            ("Goal " + str(i), "QUEUED" if i % 10 == 0 else "COMPLETED")
            for i in range(10000)
        ]
        await db.executemany(
            "INSERT INTO missions (goal, status) VALUES (?, ?)",
            missions
        )

        print("Inserting 10,000 tasks...")
        tasks = [
            (i % 10000 + 1, f"Task {i}", "Agent", "PENDING" if i % 5 == 0 else "COMPLETED")
            for i in range(10000)
        ]
        await db.executemany(
            "INSERT INTO tasks (mission_id, description, assigned_agent, status) VALUES (?, ?, ?, ?)",
            tasks
        )
        await db.commit()

async def run_queries():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Test 1: Query missions by status
        start = time.perf_counter()
        async with db.execute("SELECT * FROM missions WHERE status = ?", ("QUEUED",)) as cursor:
            rows = await cursor.fetchall()
        end = time.perf_counter()
        print(f"Query missions by status (QUEUED): {(end - start) * 1000:.2f}ms (found {len(rows)} rows)")

        # Test 2: Query tasks by status
        start = time.perf_counter()
        async with db.execute("SELECT * FROM tasks WHERE status = ?", ("PENDING",)) as cursor:
            rows = await cursor.fetchall()
        end = time.perf_counter()
        print(f"Query tasks by status (PENDING): {(end - start) * 1000:.2f}ms (found {len(rows)} rows)")

        # Test 3: Query tasks by mission_id
        start = time.perf_counter()
        async with db.execute("SELECT * FROM tasks WHERE mission_id = ?", (5000,)) as cursor:
            rows = await cursor.fetchall()
        end = time.perf_counter()
        print(f"Query tasks by mission_id (5000): {(end - start) * 1000:.2f}ms (found {len(rows)} rows)")

async def main():
    # Ensure DB is initialized
    from squad_os.database.session import init_db
    await init_db()

    await setup_data()
    print("\n--- Running Benchmark ---")
    for _ in range(3): # Run 3 times to get stable results
        await run_queries()

if __name__ == "__main__":
    asyncio.run(main())
