import os
import subprocess
import asyncio
import json
from typing import Dict, Any, Optional, List

try:
    from duckduckgo_search import DDGS
except ImportError:
    from ddgs import DDGS

from squad_os.tools.base import BaseTool
from squad_os.core.utils import is_safe_path

class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search the internet for real-time information and trends."
    parameters = {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
    async def execute(self, query: str) -> str:
        # Security: Input validation and sanitization
        if not query or not query.strip():
            return "Error: Empty search query."

        sanitized_query = query.strip()[:255] # Limit length to prevent DoS

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(sanitized_query, max_results=5))
                return "\n\n".join([f"Title: {r['title']}\nLink: {r['href']}\nSnippet: {r['body']}" for r in results])
        except Exception as e: return f"Search error: {str(e)}"

class FileWriterTool(BaseTool):
    name = "write_file"
    description = "Write content to a file. Restricted to the current project branch."
    parameters = {"type": "object", "properties": {"filename": {"type": "string"}, "content": {"type": "string"}}, "required": ["filename", "content"]}
    def __init__(self, branch_id: Optional[str] = None):
        self.workspace = os.path.join("workspace", "projects", branch_id) if branch_id else "workspace"

    async def execute(self, filename: str, content: str) -> str:
        # Security check: Prevent path traversal
        if not is_safe_path(self.workspace, filename):
            return f"Error: Access denied. Path '{filename}' is outside the workspace."

        if not os.path.exists(self.workspace): os.makedirs(self.workspace, exist_ok=True)
        # Use os.path.basename to be doubly safe, but validation already ensures it's within workspace
        filepath = os.path.join(self.workspace, os.path.basename(filename))
        with open(filepath, "w", encoding="utf-8") as f: f.write(content)
        return f"File '{filename}' written successfully to {self.workspace}."

class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read the content of a file. Can read from project root or uploads/ subdirectory."
    parameters = {"type": "object", "properties": {"filename": {"type": "string"}}, "required": ["filename"]}
    def __init__(self, branch_id: Optional[str] = None):
        self.workspace = os.path.join("workspace", "projects", branch_id) if branch_id else "workspace"

    async def execute(self, filename: str) -> str:
        # Security check: Prevent path traversal
        if not is_safe_path(self.workspace, filename):
            return f"Error: Access denied. Path '{filename}' is outside the workspace."

        # Try direct path
        filepath = os.path.join(self.workspace, filename)
        if os.path.exists(filepath) and os.path.isfile(filepath):
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f: return f.read()

        # Try basename in workspace
        filepath = os.path.join(self.workspace, os.path.basename(filename))
        if os.path.exists(filepath) and os.path.isfile(filepath):
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f: return f.read()

        # Try in uploads/
        filepath = os.path.join(self.workspace, "uploads", os.path.basename(filename))
        if os.path.exists(filepath) and os.path.isfile(filepath):
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f: return f.read()

        return f"Error: File {filename} not found in {self.workspace} or its uploads/ folder."

class TerminalTool(BaseTool):
    name = "terminal"
    description = "Execute shell commands. Restricted to the current project branch."
    parameters = {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}
    def __init__(self, branch_id: Optional[str] = None):
        self.workspace = os.path.realpath(os.path.join("workspace", "projects", branch_id)) if branch_id else os.path.realpath("workspace")

    async def execute(self, command: str) -> str:
        if not os.path.exists(self.workspace): os.makedirs(self.workspace, exist_ok=True)
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.workspace
        )
        stdout, stderr = await process.communicate()
        return f"STDOUT: {stdout.decode()}\nSTDERR: {stderr.decode()}"

class PythonRunnerTool(BaseTool):
    name = "python_runner"
    description = "Execute Python code. Restricted to the current project branch."
    parameters = {"type": "object", "properties": {"code": {"type": "string"}, "filename": {"type": "string"}}, "required": ["code", "filename"]}
    def __init__(self, branch_id: Optional[str] = None):
        self.workspace = os.path.join("workspace", "projects", branch_id) if branch_id else "workspace"

    async def execute(self, code: str, filename: str) -> str:
        # Security check: Prevent path traversal
        if not is_safe_path(self.workspace, filename):
            return f"Error: Access denied. Path '{filename}' is outside the workspace."

        if not os.path.exists(self.workspace): os.makedirs(self.workspace, exist_ok=True)
        filepath = os.path.join(self.workspace, os.path.basename(filename))
        with open(filepath, "w", encoding="utf-8") as f: f.write(code)
        process = await asyncio.create_subprocess_exec(
            "python", filepath,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.workspace
        )
        stdout, stderr = await process.communicate()
        err = stderr.decode().strip()
        if err: return f"EXECUTION_ERROR:\n{err}"
        return f"SUCCESS:\n{stdout.decode().strip()}"

class DashboardApprovalTool(BaseTool):
    name = "dashboard_approval"
    description = "Request human permission via the Dashboard."
    parameters = {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]}
    async def execute(self, message: str) -> str:
        from squad_os.database.session import create_approval_request, get_approval_status
        approval_id = await create_approval_request(mission_id=0, task_id=0, message=message)
        while True:
            response = await get_approval_status(approval_id)
            if response and response['status'] != "PENDING":
                if response['status'] == "APPROVED": return "Approved. Proceed."
                return f"Rejected. Feedback: {response['feedback']}"
            await asyncio.sleep(2)

class MemorySearchTool(BaseTool):
    name = "memory_search"
    description = "Search long-term memory for past mission data."
    parameters = {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
    async def execute(self, query: str) -> str:
        from squad_os.database.session import search_past_memory
        results = await search_past_memory(query)
        if not results: return "No memories found."
        return "\n".join([f"Agent: {r['assigned_agent']}\nData: {r['output_data'][:200]}" for r in results])

class SetSharedValueTool(BaseTool):
    name = "set_shared_value"
    description = "Store data on the Global Blackboard for other agents to see."
    parameters = {"type": "object", "properties": {"key": {"type": "string"}, "value": {"type": "string"}}, "required": ["key", "value"]}
    async def execute(self, key: str, value: str) -> str:
        from squad_os.database.session import update_blackboard
        await update_blackboard(key, value)
        return f"Key '{key}' published to blackboard."

class GetSharedValueTool(BaseTool):
    name = "get_shared_value"
    description = "Read data from the Global Blackboard."
    parameters = {"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]}
    async def execute(self, key: str) -> str:
        from squad_os.database.session import read_blackboard
        val = await read_blackboard(key)
        return f"Value for '{key}': {val}" if val else "Key not found."

class CommitProjectTool(BaseTool):
    name = "commit_project"
    description = "Commit the current project branch, moving specified artifacts to final_outputs and archiving the branch."
    parameters = {
        "type": "object",
        "properties": {
            "artifacts": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of relative file paths within the project branch to commit"
            }
        },
        "required": ["artifacts"]
    }

    def __init__(self, agent=None):
        self.agent = agent
        self.active_branch = None  # Injected by BaseAgent at runtime

    async def execute(self, artifacts: List[str]) -> str:
        branch = self.active_branch or (self.agent.active_branch if self.agent else None)
        if not branch:
            return "Error: No active project branch to commit."
        try:
            committed_paths = await branch.commit(artifacts)
            return f"Project committed successfully. Artifacts moved to: {committed_paths}. Branch archived."
        except Exception as e:
            print(f"  [CommitProjectTool ERROR]: {str(e)}")
            return f"Commit error: {str(e)}"
class DelegateTaskTool(BaseTool):
    name = "delegate_task"
    description = "Hire a specialized sub-agent for an expert task. Returns findings."
    parameters = {
        "type": "object", 
        "properties": {"specialist_role": {"type": "string"}, "task_description": {"type": "string"}},
        "required": ["specialist_role", "task_description"]
    }
    async def execute(self, specialist_role: str, task_description: str) -> str:
        from squad_os.agents.base import BaseAgent
        print(f"🤝 [Handshake]: Delegating to a temporary '{specialist_role}'...")
        
        # Equip sub-agent with the "Expert Kit"
        expert_kit = [WebSearchTool(), PythonRunnerTool(), GetSharedValueTool(), SetSharedValueTool()]
        
        sub_agent = BaseAgent(
            role=specialist_role,
            goal=task_description,
            backstory=f"You are a sub-contracted expert helping with: {task_description}",
            tools=expert_kit,
            model_name="ollama/deepseek-v3.1:671b-cloud"
        )
        result = await sub_agent.execute_task(task_description, "Context: Working as a specialist.")
        output = result.get("output") or "No output returned."
        return f"DELEGATED RESULT FROM {specialist_role}: {output}"