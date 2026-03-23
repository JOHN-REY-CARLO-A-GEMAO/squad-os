import asyncio
import os
import logging
from dotenv import load_dotenv
from squad_os.agents.base import BaseAgent
from squad_os.orchestrator.manager import Manager
from squad_os.tools.registry import WebScraperTool, FileWriterTool, SearchTool
from squad_os.database.session import init_db

# Load API keys
load_dotenv()

async def main():
    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # Initialize the mission database
    await init_db()

    # Define tools
    scraper = WebScraperTool()
    writer = FileWriterTool()
    searcher = SearchTool()

    # Define agents
    researcher = BaseAgent(
        role="Researcher",
        goal="Gather comprehensive data on the specified topic and summarize it.",
        backstory="An expert at finding the most relevant and up-to-date information.",
        tools=[scraper, searcher],
        model_name="gpt-4o-mini"
    )

    developer = BaseAgent(
        role="Developer",
        goal="Write clean, production-ready Python code (Flask/SQL) and save it to the workspace.",
        backstory="A senior software engineer specializing in web development.",
        tools=[writer],
        model_name="gpt-4o-mini"
    )

    qa = BaseAgent(
        role="QA/Reviewer",
        goal="Validate the final code against the user prompt and ensure it is bug-free.",
        backstory="A meticulous software tester with an eye for detail.",
        tools=[],
        model_name="gpt-4o-mini"
    )

    # Initialize the Manager
    squad_manager = Manager(agents=[researcher, developer, qa], model_name="gpt-4o-mini")

    # The mission goal
    mission_goal = "Create a modern Flask-based web application that displays a list of top 5 multi-agent frameworks, including SquadOS. Use a SQLite database to store the list."

    print(f"--- Starting Mission: {mission_goal} ---")
    result = await squad_manager.run_mission(mission_goal)
    print("\n--- Mission Summary ---\n")
    print(result)

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY is not set in the environment.")
    else:
        asyncio.run(main())
