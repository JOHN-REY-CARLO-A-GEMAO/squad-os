import asyncio
import warnings
from squad_os.orchestrator.manager import Manager

# CORE & REGISTRY TOOLS
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
        CommitProjectTool(agent=None),
        
        # VISUAL CAPABILITIES ACTIVATED:
        BrowserControlTool(),
        VisionAnalysisTool()
    ]
    
    # 3. Initialize the Manager with the full toolset
    # Using the powerful 671B model for complex orchestration
    manager = Manager(tool_inventory=inventory, model_name="ollama/deepseek-v3.1:671b-cloud")

    print("\n🛰️  SquadOS 'Integrated Ecosystem' Worker is ONLINE.")
    print("🚀 Level 6 Capabilities Active: Dynamic Hiring + Agent-to-Agent Delegation.")
    print("--- Waiting for missions ---")

    # 4. The Polling Loop
    while True:
        mission = await get_next_queued_mission()
        
        if mission:
            print(f"\n⚡ PICKING UP MISSION #{mission['id']}: {mission['goal']}")
            
            # Mark as in progress so other workers don't grab it
            await update_mission(mission['id'], "IN_PROGRESS")
            
            try:
                # EXECUTE MISSION
                await manager.run_mission(mission['goal'], mission.get('uploaded_files'))
                print(f"✅ MISSION #{mission['id']} COMPLETE.")
            except Exception as e:
                print(f"❌ MISSION #{mission['id']} FAILED: {e}")
                await update_mission(mission['id'], "FAILED")
        
        # Check for new requests every 5 seconds
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(run_worker())