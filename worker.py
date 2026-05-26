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

from squad_os.database.session import init_db, get_next_queued_mission, update_mission, get_next_followup_mission

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
        HITLInterruptTool()
    ]
    
    # 3. Initialize the Manager with the full toolset
    # Using free Ollama cloud model
    manager = Manager(tool_inventory=inventory, model_name="ollama/glm-4.7")

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
                print(f"\n📅 SCHEDULE TRIGGER: Running scheduled mission (ID: {schedule['id']})")
                await update_mission(schedule['id'], "IN_PROGRESS")
                try:
                    await manager.run_mission(schedule['mission_goal'], None)
                    await ScheduleManager.update_schedule_after_run(schedule['id'], schedule['id'], "COMPLETED")
                    print(f"✅ SCHEDULED MISSION #{schedule['id']} COMPLETE.")
                except Exception as e:
                    print(f"❌ SCHEDULED MISSION #{schedule['id']} FAILED: {e}")
                    await ScheduleManager.update_schedule_after_run(schedule['id'], schedule['id'], "FAILED")
        except Exception as e:
            print(f"⚠️ [Worker]: Schedule check error: {e}")
        
        # Check for queued missions
        mission = await get_next_queued_mission()
        
        if mission:
            print(f"\n⚡ PICKING UP MISSION #{mission['id']}: {mission['goal']}")
            
            # Mark as in progress so other workers don't grab it
            await update_mission(mission['id'], "IN_PROGRESS")
            
            try:
                # EXECUTE MISSION — pass workflow_json if present for pre-built DAG execution
                workflow_json = mission.get('workflow_json')
                await manager.run_mission(mission['goal'], mission.get('uploaded_files'), workflow_json)
                print(f"✅ MISSION #{mission['id']} COMPLETE.")
                await update_mission(mission['id'], "COMPLETED")
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