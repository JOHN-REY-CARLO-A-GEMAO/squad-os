"""Launches the SquadOS worker with a clean database and the gemma4 model."""

import asyncio
import sys
import os

os.environ["PYTHONIOENCODING"] = "utf-8"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

os.environ["SQUAD_OS_WORKER_VERSION"] = "2026-05-31-v2"
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("ANTHROPIC_BASE_URL", None)

from squad_os.database.session import init_db, update_mission
from squad_os.orchestrator.manager import Manager
from squad_os.tools.registry import (
    FileWriterTool, ReadFileTool, TerminalTool,
    PythonRunnerTool, CommitProjectTool,
)
from squad_os.database.session import get_next_queued_mission


async def main():
    await init_db()
    inventory = [
        FileWriterTool(), ReadFileTool(), TerminalTool(),
        PythonRunnerTool(), CommitProjectTool(),
    ]
    manager = Manager(
        tool_inventory=inventory,
        model_name="ollama/gemma4:31b-cloud",
    )
    print("Worker initialized. Polling for missions...", flush=True)
    while True:
        mission = await get_next_queued_mission()
        if mission:
            mid = mission["id"]
            goal = mission["goal"][:80]
            print(f"\n=== PICKING UP MISSION #{mid} ===", flush=True)
            await update_mission(mid, "IN_PROGRESS")
            try:
                await manager.run_mission(mission["goal"])
                await update_mission(mid, "COMPLETED")
                print(f"=== MISSION #{mid} COMPLETE ===\n", flush=True)
            except Exception as e:
                print(f"=== MISSION #{mid} FAILED: {e} ===\n", flush=True)
                await update_mission(mid, "FAILED")
        await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
