import asyncio
import aiosqlite
from squad_os.database.session import init_db

async def submit():
    await init_db()
    async with aiosqlite.connect('instance/shared_memory.db') as db:
        await db.execute(
            "INSERT INTO missions (name, description, status) VALUES (?, ?, ?)",
            (
                "VisualDemo", 
                "DO NOT ask for human approval. DO NOT use web_search. "
                "You are a web-browsing agent. Use the BrowserControlTool to navigate to 'https://news.ycombinator.com', "
                "take a screenshot of the front page, and then use the CommitProjectTool to commit the visual artifacts.", 
                "QUEUED"
            )
        )
        await db.commit()
    print("🚀 Visual Mission submitted!")

if __name__ == "__main__":
    asyncio.run(submit())