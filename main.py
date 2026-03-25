import asyncio
import litellm
from squad_os.agents.base import BaseAgent
from squad_os.orchestrator.manager import Manager
from squad_os.tools.registry import TerminalTool, FileWriterTool, HumanApprovalTool
from squad_os.database.session import init_db

# Set timeout to prevent long waits
litellm.request_timeout = 60

async def main():
    await init_db()
    terminal = TerminalTool()
    writer = FileWriterTool()
    human = HumanApprovalTool()
    
    # Using a fast cloud model
    CLOUD_MODEL = "ollama/deepseek-v3.1:671b-cloud"

    marketer = BaseAgent(
        role="GitHub Specialist",
        goal="Rewrite the README and organize the project for maximum GitHub stars.",
        backstory="Expert in professional open-source documentation and project structure.",
        tools=[terminal, writer, human],
        model_name=CLOUD_MODEL
    )

    squad_manager = Manager(agents=[marketer], model_name=CLOUD_MODEL)

    # THE MISSION: Professional Polish
    mission_goal = (
        "1. Rewrite 'README.md' to be professional. Include: "
        "   - Badges for License and Python version. "
        "   - Sections: Features (Async, SQLite, Human-in-the-loop), Dashboard, and Examples. "
        "2. Create an 'examples/' folder and move the Java code there. "
        "3. COMMIT and PUSH to GitHub main branch. "
        "ASK FOR APPROVAL BEFORE PUSHING."
    )

    print(f"--- Starting Final Star-Maker Mission ---")
    await squad_manager.run_mission(mission_goal)
    print("\n--- DONE! Refresh GitHub now! ---")

if __name__ == "__main__":
    asyncio.run(main())