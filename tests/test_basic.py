import asyncio
import os
from squad_os.agents.base import BaseAgent
from squad_os.tools.registry import FileWriterTool
from squad_os.database.session import init_db

async def test_agent_tool():
    await init_db()
    writer = FileWriterTool()
    agent = BaseAgent(
        role="TestAgent",
        goal="Write a test file.",
        backstory="A helpful test agent.",
        tools=[writer],
        model_name="gpt-4o-mini"
    )
    
    result = await agent.execute_task("Write 'Hello SquadOS' to a file named 'hello_async.txt' in the workspace.")
    print(f"Agent result: {result}")
    
    file_path = "workspace/hello_async.txt"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            content = f.read()
            print(f"File content: {content}")
            assert content == "Hello SquadOS"
            print("Test Passed: File written correctly.")
    else:
        print("Test Failed: File not found.")

if __name__ == "__main__":
    if os.getenv("OPENAI_API_KEY"):
        asyncio.run(test_agent_tool())
    else:
        print("Skipping test: OPENAI_API_KEY not set.")
