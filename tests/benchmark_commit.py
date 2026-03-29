import os
import shutil
import time
import asyncio
from squad_os.core.projects import ProjectBranch

async def benchmark_commit():
    base_dir = "benchmark_workspace"
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)

    branch_id = "bench_project"
    branch = ProjectBranch(branch_id, base_dir=base_dir)
    branch.fork()

    # 1. Setup: Create 10,000 files in the project
    num_files = 10000
    print(f"Creating {num_files} files in {branch.project_path}...")
    for i in range(num_files):
        # Create some nested structure too
        if i % 100 == 0:
            os.makedirs(os.path.join(branch.project_path, f"subdir_{i//100}"), exist_ok=True)
            path = os.path.join(branch.project_path, f"subdir_{i//100}", f"file_{i}.txt")
        else:
            path = os.path.join(branch.project_path, f"file_{i}.txt")

        with open(path, "w") as f:
            f.write(f"Content for file {i}")

    # Create some files in visuals/
    for i in range(10):
        with open(os.path.join(branch.visuals_path, f"artifact_{i}.png"), "w") as f:
            f.write(f"Image data {i}")

    # 2. Define 10 artifacts to commit
    artifacts = [f"artifact_{i}.png" for i in range(10)]

    # 3. Measure commit time
    print(f"Committing {len(artifacts)} artifacts...")
    start_time = time.perf_counter()
    await branch.commit(artifacts)
    end_time = time.perf_counter()

    duration = end_time - start_time
    print(f"Commit took: {duration:.4f} seconds")

    # Cleanup
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)

    return duration

if __name__ == "__main__":
    asyncio.run(benchmark_commit())
