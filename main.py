import asyncio
import litellm
from squad_os.agents.base import BaseAgent
from squad_os.orchestrator.manager import Manager
from squad_os.tools.registry import (
    TerminalTool, 
    FileWriterTool, 
    HumanApprovalTool, 
    WebSearchTool  # Added for research capabilities
)
from squad_os.database.session import init_db

# Set timeout to prevent long waits
litellm.request_timeout = 60

async def main():
    # 1. Initialize the shared memory database
    await init_db()

    # 2. Initialize tools
    terminal = TerminalTool()
    writer = FileWriterTool()
    human = HumanApprovalTool()
    search = WebSearchTool()
    
    # Model configuration
    CLOUD_MODEL = "ollama/deepseek-v3.1:671b-cloud"

    # 3. Define the Squad (Multiple specialized personas)
    
    # The Researcher: Finds information
    researcher = BaseAgent(
        role="Market Researcher",
        goal="Find the top 3 trending features in open-source AI frameworks today.",
        backstory="Expert at parsing GitHub trends and developer forums to find what users want.",
        tools=[search],
        model_name=CLOUD_MODEL
    )

    # The Technical Writer: Takes research and creates files
    writer_agent = BaseAgent(
        role="Technical Content Creator",
        goal="Write high-quality Markdown documentation based on research data.",
        backstory="A documentation specialist who excels at making complex technical features sound exciting.",
        tools=[writer],
        model_name=CLOUD_MODEL
    )

    # The QA Reviewer: Triggers the "QA Loop" logic in the Manager
    # Note: Using 'QA' in the role name triggers the Manager's retry logic if it fails.
    reviewer = BaseAgent(
        role="QA Specialist",
        goal="Review documentation for technical accuracy and professional tone.",
        backstory="A strict editor who rejects work if it's too short (under 200 words) or contains placeholders.",
        tools=[human], 
        model_name=CLOUD_MODEL
    )

    # 4. Initialize the Manager with the full squad
    squad_manager = Manager(
        agents=[researcher, writer_agent, reviewer], 
        model_name=CLOUD_MODEL
    )

    # 5. THE MISSION: A multi-step goal that requires collaboration
    mission_goal = (
        "1. Research the 3 most requested features for AI Agent frameworks in 2024. "
        "2. Create a file named 'ROADMAP.md' in the workspace. "
        "3. Write a detailed roadmap proposal in that file based on the research. "
        "4. The QA Specialist must review the file. If it's not detailed enough, it must be rewritten."
    )

    print(f"--- 🚀 SquadOS Mission Started: Roadmap Generation ---")
    
    try:
        await squad_manager.run_mission(mission_goal)
        print("\n--- ✅ MISSION ACCOMPLISHED ---")
        print("Check the 'workspace/ROADMAP.md' file and 'shared_memory.db' for the audit log.")
    except Exception as e:
        print(f"\n--- ❌ MISSION FAILED ---")
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
