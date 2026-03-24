import os
import aiohttp
from typing import Any, Dict
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from .base import BaseTool

WORKSPACE_DIR = os.path.abspath("workspace")

class WebScraperTool(BaseTool):
    @property
    def name(self) -> str:
        return "web_scrape"

    @property
    def description(self) -> str:
        return "Scrapes a URL and returns its content in Markdown format."

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
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    # Basic cleaning
                    for script in soup(["script", "style"]):
                        script.decompose()
                    return md(str(soup))
        except Exception as e:
            return f"Error scraping {url}: {str(e)}"

class FileWriterTool(BaseTool):
    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Writes content to a file in the workspace directory. Sandboxed for security."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "The path to the file relative to the workspace"},
                "content": {"type": "string", "description": "The content to write"}
            },
            "required": ["filepath", "content"]
        }

    async def execute(self, filepath: str, content: str) -> str:
        # Security: restrict to workspace directory
        abs_path = os.path.abspath(os.path.join(WORKSPACE_DIR, filepath))
        if not abs_path.startswith(WORKSPACE_DIR):
            return "Error: Access denied. You can only write to the workspace directory."
        
        try:
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w") as f:
                f.write(content)
            return f"Successfully wrote to {filepath}"
        except Exception as e:
            return f"Error writing file: {str(e)}"

class SearchTool(BaseTool):
    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Searches the web for high-quality information using the Tavily API."

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
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return "Error: TAVILY_API_KEY not found in environment. Mocking results: Flask is a micro web framework for Python."

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": api_key,
            "query": query,
            "search_depth": "advanced",
            "include_images": False,
            "include_answer": True,
            "max_results": 5
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("results", [])
                        formatted_results = []
                        for res in results:
                            formatted_results.append(f"Title: {res['title']}\nURL: {res['url']}\nContent: {res['content']}\n")
                        return "\n---\n".join(formatted_results)
                    else:
                        return f"Error from Tavily API: {response.status} - {await response.text()}"
        except Exception as e:
            return f"Error executing search: {str(e)}"
