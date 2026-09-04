import os
import asyncio
import json
import warnings
from dotenv import load_dotenv
load_dotenv()
from squad_os.orchestrator.manager import Manager

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

# VIDEO PROCESSING
from squad_os.tools.video import (
    VideoProcessingTool   # <--- Watermark removal, video editing
)

# NATIVE INTEGRATIONS
from squad_os.tools.telegram import TelegramTool, TelegramReceiveTool
from squad_os.tools.discord import DiscordTool, DiscordReceiveTool
from squad_os.tools.email import EmailSendTool, EmailReceiveTool

# MARKETPLACE
from squad_os.tools.marketplace import SkillMarketplaceTool, InstallSkillTool, GetToolInfoTool

# SCHEDULING
from squad_os.tools.scheduler import (
    ScheduleMissionTool,
    ListSchedulesTool,
    CancelScheduleTool,
    PauseScheduleTool,
    ResumeScheduleTool,
    ScheduleManager
)

# SELF-HEALING
from squad_os.tools.self_healing import (
    SelfHealTool,
    HealthCheckTool,
    RetryWithBackoffTool,
    health_monitor
)

# RICH HITL
from squad_os.tools.hitl import (
    RichApprovalTool,
    NotifyHumanTool,
    HITLInterruptTool,
    HITLWebSocketServer
)

# MULTIMEDIA / CREATIVE ENGINE (Phase 2‑3)
from squad_os.tools.media import ImageGenTool, VideoGenTool, NeuralAudioTool, AdvancedVideoEditorTool

# MCP CONNECTIVITY (Phase 1)
from squad_os.tools.mcp_hub import MCPWrapperTool, MCPListTool, MCPRegisterTool

# SYSTEM MONITORING (Phase 1)
from squad_os.tools.system import SystemMonitorTool, SystemSummaryTool

# SQUAD SYNC / INTERCONNECT (Phase 3)
from squad_os.tools.sync import SquadDiscoverTool, SquadBlackboardTool, SquadResourceTool

# GPU OFFLOAD / COMPUTE DELEGATE (Phase 3)
from squad_os.tools.compute import ComputeDelegateTool, ComputeStatusTool, GPUInfoTool

# SELF‑IMPROVEMENT / EVOLUTION (Phase 3)
from squad_os.tools.evolution import EvolutionTool

from squad_os.database.session import init_db, create_mission, get_next_queued_mission, update_mission, get_next_followup_mission


# Code version — bump this when making breaking changes so old workers detect stale code
WORKER_VERSION = "2026-05-31-v2"

# Clean up terminal warnings
warnings.filterwarnings("ignore", category=ResourceWarning)

async def run_worker():
    # Stale-code guard: compare source version against an env marker set by the launcher
    expected = os.environ.get("SQUAD_OS_WORKER_VERSION", WORKER_VERSION)
    if expected != WORKER_VERSION:
        print(f"[Worker] CODE VERSION MISMATCH: expected={expected}, loaded={WORKER_VERSION}")
        print("[Worker] Restart required. Shutting down for launcher to respawn.")
        return

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
        CommitProjectTool(),
        
        # VISUAL CAPABILITIES ACTIVATED:
        BrowserControlTool(),
        VisionAnalysisTool(),

        # VIDEO PROCESSING:
        VideoProcessingTool(),
        
        # NATIVE INTEGRATIONS:
        TelegramTool(),
        TelegramReceiveTool(),
        DiscordTool(),
        DiscordReceiveTool(),
        EmailSendTool(),
        EmailReceiveTool(),
        
        # MARKETPLACE:
        SkillMarketplaceTool(),
        InstallSkillTool(),
        GetToolInfoTool(),
        
        # SCHEDULING:
        ScheduleMissionTool(),
        ListSchedulesTool(),
        CancelScheduleTool(),
        PauseScheduleTool(),
        ResumeScheduleTool(),
        
        # SELF-HEALING:
        SelfHealTool(),
        HealthCheckTool(),
        RetryWithBackoffTool(),
        
        # RICH HITL:
        RichApprovalTool(),
        NotifyHumanTool(),
        HITLInterruptTool(),

        # MULTIMEDIA / CREATIVE ENGINE:
        ImageGenTool(),
        VideoGenTool(),
        NeuralAudioTool(),
        AdvancedVideoEditorTool(),

        # MCP CONNECTIVITY:
        MCPWrapperTool(),
        MCPListTool(),
        MCPRegisterTool(),

        # SYSTEM MONITORING:
        SystemMonitorTool(),
        SystemSummaryTool(),

        # SQUAD SYNC / INTERCONNECT:
        SquadDiscoverTool(),
        SquadBlackboardTool(),
        SquadResourceTool(),

        # GPU OFFLOAD / COMPUTE DELEGATE:
        ComputeDelegateTool(),
        ComputeStatusTool(),
        GPUInfoTool(),

        # SELF-IMPROVEMENT / EVOLUTION:
        EvolutionTool()
    ]

    # Discover tools from installed .sqad packages and add to inventory
    try:
        from squad_os.tools.marketplace import SkillRegistry
        registry = SkillRegistry.get_instance()
        existing_names = {t.name for t in inventory}
        for info in registry.list_tools():
            name = info["name"]
            if name not in existing_names:
                tool = registry.get_tool(name)
                if tool:
                    inventory.append(tool)
                    existing_names.add(name)
    except Exception as e:
        print(f"[Worker] Package tool discovery: {e}")

    # 3. Initialize the Manager with the full toolset
    # Using Gemma via Ollama Cloud
    manager = Manager(tool_inventory=inventory, model_name="ollama/gemma4:31b-cloud")

    print("\n🛰️  SquadOS 'Integrated Ecosystem' Worker is ONLINE.")
    print("🚀 Level 6 Capabilities Active: Dynamic Hiring + Agent-to-Agent Delegation.")
    print("📅 Scheduling Engine Active: Cron-like mission scheduling enabled.")
    print("📡 HITL WebSocket Server: Real-time human-in-the-loop notifications.")
    print("--- Waiting for missions ---")

    # Start WebSocket server for HITL notifications
    ws_task = None
    try:
        ws_server = HITLWebSocketServer.get_instance()
        ws_task = asyncio.create_task(ws_server.start())
    except Exception as e:
        print(f"⚠️ [Worker]: HITL WebSocket server failed to start: {e}")
        print("   Falling back to polling-based HITL.")

    # 4. The Polling Loop
    while True:
        # Check for scheduled missions first
        try:
            due_schedules = await ScheduleManager.get_due_schedules()
            for schedule in due_schedules:
                print(f"\n📅 SCHEDULE TRIGGER: Running scheduled mission (Schedule ID: {schedule['id']})")
                # A schedule row is not a mission row — create one per run so tasks,
                # interrupts and history attach to a real mission. run_mission reuses
                # it (no duplicate rows), sets its status and returns the outcome.
                mission_id = await create_mission(schedule['mission_goal'])
                try:
                    outcome = await manager.run_mission(schedule['mission_goal'], None, mission_id=mission_id)
                    await ScheduleManager.update_schedule_after_run(schedule['id'], mission_id, outcome or "FAILED")
                    print(f"✅ SCHEDULE #{schedule['id']} → MISSION #{mission_id} {outcome}.")
                except Exception as e:
                    print(f"❌ SCHEDULE #{schedule['id']} (mission #{mission_id}) FAILED: {e}")
                    await update_mission(mission_id, "FAILED")
                    await ScheduleManager.update_schedule_after_run(schedule['id'], mission_id, "FAILED")
        except Exception as e:
            print(f"⚠️ [Worker]: Schedule check error: {e}")
        
        # Check for queued missions
        mission = await get_next_queued_mission()
        
        if mission:
            print(f"\n⚡ PICKING UP MISSION #{mission['id']}: {mission['goal']}")
            
            # Mark as in progress so other workers don't grab it
            await update_mission(mission['id'], "IN_PROGRESS")
            
            try:
                # EXECUTE MISSION — pass the queue row's id so tasks/interrupts
                # attach to the SAME mission the human queued (no duplicate rows).
                # run_mission returns the real outcome and sets the mission status.
                workflow_json = mission.get('workflow_json')
                outcome = await manager.run_mission(mission['goal'], mission.get('uploaded_files'), workflow_json, mission_id=mission['id'])
                print(f"{'✅' if outcome == 'COMPLETED' else '❌' if outcome == 'FAILED' else '⏸️'} MISSION #{mission['id']} {outcome}.")
            except Exception as e:
                print(f"❌ MISSION #{mission['id']} FAILED: {e}")
                await update_mission(mission['id'], "FAILED")
        
        # Check for follow-up missions (status = 'FOLLOWUP')
        followup = await get_next_followup_mission()
        if followup:
            print(f"\n💬 FOLLOW-UP DETECTED for MISSION #{followup['id']}: {followup['goal'][:60]}...")
            await update_mission(followup['id'], "IN_PROGRESS")
            try:
                # Get the last user message from conversation history as the follow-up text
                history = json.loads(followup.get('conversation_history') or '[]')
                last_user_msg = ""
                for msg in reversed(history):
                    if msg.get('role') == 'user':
                        last_user_msg = msg.get('content', '')
                        break
                if last_user_msg:
                    await manager.handle_followup(followup['id'], last_user_msg)
                    print(f"✅ FOLLOW-UP FOR MISSION #{followup['id']} COMPLETE.")
                else:
                    print(f"⚠️ FOLLOW-UP FOR MISSION #{followup['id']} has no user message.")
                    await update_mission(followup['id'], "COMPLETED")
            except Exception as e:
                print(f"❌ FOLLOW-UP FOR MISSION #{followup['id']} FAILED: {e}")
                await update_mission(followup['id'], "FAILED")
        
        # Check for new requests every 5 seconds
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(run_worker())