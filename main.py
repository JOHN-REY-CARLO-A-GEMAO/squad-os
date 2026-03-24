import asyncio
from squad_os.agents.base import BaseAgent
from squad_os.orchestrator.manager import Manager
from squad_os.tools.registry import TerminalTool, HumanApprovalTool
from squad_os.database.session import init_db

async def main():
    await init_db()
    terminal = TerminalTool()
    human = HumanApprovalTool() # Initialize the new tool
    
    CLOUD_MODEL = "ollama/gpt-oss:20b-cloud"

    # Define the Agent
    # We tell the agent in its backstory that it MUST ask for permission.
    devops = BaseAgent(
        role="DevOps Engineer",
        goal="Push the current workspace changes to GitHub safely.",
        backstory=(
            "You are a careful engineer. You have access to the terminal, "
            "but you MUST use the human_approval tool before running any 'git push' command."
        ),
        tools=[terminal, human], # Give it both tools
        model_name=CLOUD_MODEL
    )

    squad_manager = Manager(agents=[devops], model_name=CLOUD_MODEL)

    mission_goal = (
        "1. Check the git status. "
        "2. Propose a commit message for the recent changes. "
        "3. ASK the human for approval to push to the main branch. "
        "4. If approved, execute the push."
    )

    print(f"--- Starting Safety-First Mission ---")
    await squad_manager.run_mission(mission_goal)
    print("\n--- Mission Complete ---")

if __name__ == "__main__":
    asyncio.run(main())