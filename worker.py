import asyncio
import warnings
from squad_os.orchestrator.manager import Manager
from squad_os.core.logging import setup_root_logger, get_logger
from squad_os.core.guardrails import screen_input, SafetyLevel

# CORE & REGISTRY TOOLS
from squad_os.tools.desktop import DesktopControlTool
from squad_os.tools.ui_inspector import UIInspectorTool
from squad_os.tools.registry import (
    WebSearchTool,
    FileWriterTool,
    ReadFileTool,
    TerminalTool,
    PythonRunnerTool,
    DashboardApprovalTool,
    MemorySearchTool,
    SetSharedValueTool,
    GetSharedValueTool,
    DelegateTaskTool,
    CommitProjectTool     # <--- Commits the final branch
)

# VISUAL & BROWSER TOOLS
from squad_os.tools.visual import (
    BrowserControlTool,   # <--- The Agent's Camera/Browser
    VisionAnalysisTool    # <--- The Agent's Visual Analyzer
)

from squad_os.database.session import init_db, get_next_queued_mission, update_mission

# Clean up terminal warnings
warnings.filterwarnings("ignore", category=ResourceWarning)

async def run_worker():
    # 0. Initialize structured logging
    setup_root_logger()
    log = get_logger("squad_os.worker")

    # 1. Initialize the database and create the new Blackboard table
    await init_db()

    # 2. Tool Inventory: Everything the Manager can 'equip' a new hire with
    inventory = [
        WebSearchTool(),
        FileWriterTool(),
        ReadFileTool(),
        TerminalTool(),
        PythonRunnerTool(),
        DashboardApprovalTool(),
        MemorySearchTool(),
        SetSharedValueTool(),
        GetSharedValueTool(),
        DelegateTaskTool(),
        DesktopControlTool(),
        UIInspectorTool(),
        CommitProjectTool(agent=type('obj', (object,), {'active_branch': None})()),

        # VISUAL CAPABILITIES ACTIVATED:
        BrowserControlTool(),
        VisionAnalysisTool()
    ]

    # 3. Initialize the Manager with the full toolset
    # Using the powerful 671B model for complex orchestration
    manager = Manager(tool_inventory=inventory, model_name="ollama/deepseek-v3.1:671b-cloud")

    log.info("SquadOS worker is ONLINE", capabilities="Dynamic Hiring + Agent-to-Agent Delegation")

    # 4. The Polling Loop
    while True:
        mission = await get_next_queued_mission()

        if mission:
            mission_log = log.bind(mission_id=mission['id'])
            goal = mission['goal']

            # Layer 0: Input safety screening
            safety = screen_input(goal)
            if safety.is_blocked:
                mission_log.warning("Mission blocked by safety guardrail", violations=[v.description for v in safety.violations])
                await update_mission(mission['id'], "FAILED")
                continue

            if safety.level == SafetyLevel.SUSPICIOUS:
                mission_log.warning("Mission flagged as suspicious", violations=[v.description for v in safety.violations])
                # Allow suspicious missions to proceed but log them

            mission_log.info("Picking up mission", goal=goal[:100])

            # Mark as in progress so other workers don't grab it
            await update_mission(mission['id'], "IN_PROGRESS")

            try:
                # EXECUTE MISSION
                await manager.run_mission(
                    goal,
                    mission.get('uploaded_files'),
                    max_tokens=mission.get('max_tokens', 0),
                    max_turns=mission.get('max_turns', 0),
                    max_cost_usd=mission.get('max_cost_usd', 0.0),
                )
                mission_log.info("Mission complete")
                await update_mission(mission['id'], "COMPLETED")
            except Exception as e:
                mission_log.error("Mission failed", error=str(e))
                await update_mission(mission['id'], "FAILED")

        # Check for new requests every 5 seconds
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(run_worker())