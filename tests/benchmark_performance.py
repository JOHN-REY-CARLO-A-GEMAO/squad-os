import asyncio
import os
import time
import shutil
import sqlite3
from squad_os.database.session import init_db, search_past_memory, get_next_queued_mission, DB_PATH
from squad_os.core.projects import ProjectBranch

async def benchmark_db():
    print("--- DB Benchmark ---")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    await init_db()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Insert 10,000 tasks
    print("Inserting 10,000 tasks...")
    tasks = [
        (1, f"Task {i}", "agent", "COMPLETED", "output data " + str(i))
        for i in range(10000)
    ]
    cursor.executemany(
        "INSERT INTO tasks (mission_id, description, assigned_agent, status, output_data) VALUES (?, ?, ?, ?, ?)",
        tasks
    )

    # Insert 1,000 missions
    print("Inserting 1,000 missions...")
    missions = [
        (f"Goal {i}", "QUEUED")
        for i in range(1000)
    ]
    cursor.executemany(
        "INSERT INTO missions (goal, status) VALUES (?, ?)",
        missions
    )
    conn.commit()
    conn.close()

    # Benchmark search_past_memory
    start = time.perf_counter()
    for _ in range(10):
        await search_past_memory("999")
    end = time.perf_counter()
    print(f"search_past_memory (10 calls): {(end - start):.4f}s")

    # Benchmark get_next_queued_mission
    start = time.perf_counter()
    for _ in range(10):
        await get_next_queued_mission()
    end = time.perf_counter()
    print(f"get_next_queued_mission (10 calls): {(end - start):.4f}s")

async def benchmark_fs():
    print("\n--- FS Benchmark ---")
    base_dir = "benchmark_workspace"
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)

    branch = ProjectBranch("bench_id", base_dir=base_dir)
    branch.fork()

    # Create 1,000 files
    print("Creating 1,000 files...")
    for i in range(1000):
        with open(os.path.join(branch.project_path, f"file_{i}.txt"), "w") as f:
            f.write("data")

    # 10 artifacts to commit
    artifacts = [f"file_{i*100}.txt" for i in range(10)]

    start = time.perf_counter()
    await branch.commit(artifacts)
    end = time.perf_counter()
    print(f"ProjectBranch.commit (10 artifacts, 1,000 files): {(end - start):.4f}s")

    shutil.rmtree(base_dir)

if __name__ == "__main__":
    asyncio.run(benchmark_db())
    asyncio.run(benchmark_fs())
