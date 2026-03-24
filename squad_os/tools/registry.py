import os
import aiohttp
import subprocess
import asyncio  # <--- ADD THIS LINE HERE
from typing import Any, Dict
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from duckduckgo_search import DDGS
from .base import BaseTool

# Sandbox directory for file operations
WORKSPACE_DIR = os.path.abspath("workspace")
os.makedirs(WORKSPACE_DIR, exist_ok=True)

class WebScraperTool(BaseTool):
    @property
    def name(self) -> str:
        return "web_scrape"

    @property
    def description(self) -> str:
        return "Scrapes a URL and returns its content in Markdown format. Best for reading specific articles."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to scrape"}
            },
            "required": ["url"]
        }

    async def execute(self, url: str) -> str:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        return f"Error: Received status code {response.status}"
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Remove noise
                    for element in soup(["script", "style", "nav", "footer", "header"]):
                        element.decompose()
                        
                    content = md(str(soup))
                    return content[:8000] # Limit context size for LLM
        except Exception as e:
            return f"Error scraping {url}: {str(e)}"

class FileWriterTool(BaseTool):
    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Writes content to a file. Sandboxed to the 'workspace/' directory for security."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Filename (e.g., 'app.py' or 'GUI.java')"},
                "content": {"type": "string", "description": "The text/code content to write"}
            },
            "required": ["filepath", "content"]
        }

    async def execute(self, filepath: str, content: str) -> str:
        # Security: restrict to workspace directory
        abs_path = os.path.abspath(os.path.join(WORKSPACE_DIR, filepath))
        if not abs_path.startswith(WORKSPACE_DIR):
            return "Error: Security Violation. You can only write to the workspace directory."
        
        try:
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully saved to workspace/{filepath}"
        except Exception as e:
            return f"Error writing file: {str(e)}"

class SearchTool(BaseTool):
    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Real-time web search via DuckDuckGo. Use this to find news, documentation, or code examples."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"}
            },
            "required": ["query"]
        }

    async def execute(self, query: str) -> str:
        try:
            # DuckDuckGo is free and requires no API key
            with DDGS() as ddgs:
                results = [r for r in ddgs.text(query, max_results=5)]
                if not results:
                    return "No search results found."
                
                formatted = "\n\n".join([f"Source: {r['href']}\nSnippet: {r['body']}" for r in results])
                return formatted
        except Exception as e:
            return f"Search Error: {str(e)}"

class TerminalTool(BaseTool):
    @property
    def name(self) -> str:
        return "terminal"

    @property
    def description(self) -> str:
        return "Executes shell commands (git, pip, ls, etc.). Use carefully."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The shell command to run"}
            },
            "required": ["command"]
        }

    async def execute(self, command: str) -> str:
        try:
            # Run the command and capture output
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            output = f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
            return output if output.strip() else "Command executed with no output."
        except Exception as e:
            return f"Terminal Error: {str(e)}"

    import asyncio
from .base import BaseTool

class HumanApprovalTool(BaseTool):
    @property
    def name(self) -> str:
        return "human_approval"

    @property
    def description(self) -> str:
        return (
            "Pauses the agent and asks the human for approval or feedback. "
            "Use this BEFORE running critical terminal commands or finishing a major task."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Why are you asking for approval?"},
                "proposed_action": {"type": "string", "description": "What exactly are you about to do?"}
            },
            "required": ["reason", "proposed_action"]
        }

    async def execute(self, reason: str, proposed_action: str) -> str:
        print(f"\n{'='*50}")
        print(f"🛑 [AGENT WAITING FOR APPROVAL]")
        print(f"REASON: {reason}")
        print(f"ACTION: {proposed_action}")
        print(f"{'='*50}")
        
        # We use run_in_executor because 'input' is a blocking function
        loop = asyncio.get_event_loop()
        user_input = await loop.run_in_executor(
            None, lambda: input("Type 'yes' to approve, or provide feedback/corrections: ")
        )
        
        if user_input.lower() == 'yes':
            return "Approved. You may proceed with the action."
        else:
            return f"Action REJECTED by human. Human Feedback: {user_input}"