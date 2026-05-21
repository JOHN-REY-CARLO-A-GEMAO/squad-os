import os
import subprocess
import asyncio
import json
import re
import shlex
from typing import Dict, Any, Optional, List, Set

try:
    from duckduckgo_search import DDGS
except ImportError:
    from ddgs import DDGS

from squad_os.tools.base import BaseTool
from squad_os.core.utils import is_safe_path

# Security: Dangerous command patterns that are blocked
DANGEROUS_PATTERNS: Set[str] = {
    'rm -rf /', 'rm -rf /*', 'rm -rf ~', 'dd if=/dev/zero', 'mkfs.', 'fdisk',
    '>:', '>&', '/dev/null', 'shutdown', 'reboot', 'halt', 'poweroff',
    'init 0', 'telinit 0', 'kill -9 -1', 'kill -9 1',
    'curl .*|.*sh', 'curl .*|.*bash', 'wget .*|.*sh', 'wget .*|.*bash',
    '> /etc/', '>> /etc/', 'echo.*> /', 'echo.*>> /',
    'chmod 777 /', 'chmod -R 777 /', 'chown -R',
    'mkfs.ext', 'mkfs.btrfs', 'mkfs.xfs', 'parted', 'gparted',
    'del /f /s /q', 'rd /s /q', 'format ', 'diskpart',
}

# Allowed safe commands for terminal
ALLOWED_COMMANDS: Set[str] = {
    'ls', 'dir', 'pwd', 'cd', 'cat', 'type', 'head', 'tail', 'less', 'more',
    'echo', 'grep', 'find', 'wc', 'sort', 'uniq', 'diff', 'cmp',
    'mkdir', 'touch', 'cp', 'copy', 'mv', 'move', 'rm', 'del', 'rmdir', 'rd',
    'python', 'python3', 'pip', 'pip3', 'node', 'npm', 'yarn',
    'git', 'git clone', 'git status', 'git log', 'git diff', 'git show',
    'curl', 'wget', 'tar', 'zip', 'unzip', 'gzip', 'gunzip',
    'make', 'cmake', 'gcc', 'g++', 'javac', 'java', 'go', 'rustc',
    'docker', 'kubectl', 'terraform', 'ansible-playbook',
    'pytest', 'unittest', 'test', 'coverage',
    'black', 'flake8', 'pylint', 'mypy', 'isort',
    'cat', 'cut', 'awk', 'sed', 'tr', 'xargs', 'tee',
    'ssh', 'scp', 'sftp', 'rsync', 'nc', 'netcat',
    'ping', 'traceroute', 'tracert', 'nslookup', 'dig', 'host',
    'ps', 'top', 'htop', 'df', 'du', 'free', 'uptime', 'whoami', 'id',
    'stat', 'file', 'which', 'where', 'whereis', 'locate', 'updatedb',
    'openssl', 'ssh-keygen', 'gpg', 'md5sum', 'sha256sum', 'shasum',
    'base64', 'hexdump', 'xxd', 'od', 'strings',
    'tree', 'fzf', 'rg', 'fd', 'ag', 'pt', 'ack',
}


def _is_dangerous_command(command: str) -> bool:
    """Check if command contains dangerous patterns."""
    cmd_lower = command.lower().strip()
    for pattern in DANGEROUS_PATTERNS:
        if pattern.lower() in cmd_lower:
            return True
    # Check for shell injection patterns
    if re.search(r'`[^`]+`', cmd_lower) or re.search(r'\$\([^)]+\)', cmd_lower):
        return True
    return False


def _validate_terminal_command(command: str, workspace: str) -> tuple[bool, str]:
    """Validate terminal command against allowlist and dangerous patterns."""
    if not command or not command.strip():
        return False, "Empty command not allowed"

    if _is_dangerous_command(command):
        return False, "Command contains dangerous patterns and is blocked for security"

    try:
        tokens = shlex.split(command)
        if not tokens:
            return False, "Could not parse command"
    except ValueError as e:
        return False, f"Shell parsing error: {e}"

    operators = {";", "&&", "||", "|", "&", "|&"}
    redirections = {">", ">>", "<", "2>", "1>", "&>", ">&"}

    expect_command = True
    for token in tokens:
        if token in operators:
            expect_command = True
            continue

        if expect_command:
            base_cmd = token
            if '/' in base_cmd or '\\' in base_cmd:
                base_cmd = os.path.basename(base_cmd)

            if base_cmd.lower() not in ALLOWED_COMMANDS and not token.startswith('./'):
                return False, f"Command '{token}' not in allowed command list"
            expect_command = False
            # Fall through to path check for the command itself if it has paths

        # Check all tokens for path traversal
        path_candidate = token
        for red in redirections:
            if token.startswith(red):
                path_candidate = token[len(red):]
                break

        if path_candidate and any(c in path_candidate for c in ('/', '\\', '..')):
            if not is_safe_path(workspace, path_candidate):
                return False, f"Access denied: '{path_candidate}' is outside the workspace"

    return True, ""


# Dangerous Python code patterns
DANGEROUS_PYTHON_PATTERNS: List[tuple[str, str]] = [
    (r'\b__import__\s*\(\s*["\']os["\']', "Blocked: dynamic import of os module"),
    (r'\b__import__\s*\(\s*["\']subprocess["\']', "Blocked: dynamic import of subprocess"),
    (r'\b__import__\s*\(\s*["\']sys["\']', "Blocked: dynamic import of sys module"),
    (r'\b__import__\s*\(\s*["\']shutil["\']', "Blocked: dynamic import of shutil module"),
    (r'\beval\s*\(', "Blocked: eval() is dangerous"),
    (r'\bexec\s*\(', "Blocked: exec() is dangerous"),
    (r'\bcompile\s*\(', "Blocked: compile() can be used for code injection"),
    (r'os\.system\s*\(', "Blocked: os.system() is dangerous"),
    (r'os\.popen\s*\(', "Blocked: os.popen() is dangerous"),
    (r'os\.spawn', "Blocked: os.spawn* is dangerous"),
    (r'os\.fork', "Blocked: os.fork() is dangerous"),
    (r'subprocess\.call', "Blocked: subprocess.call() is dangerous"),
    (r'subprocess\.run', "Blocked: subprocess.run() is dangerous"),
    (r'subprocess\.Popen', "Blocked: subprocess.Popen() is dangerous"),
    (r'subprocess\.check_output', "Blocked: subprocess.check_output() is dangerous"),
    (r'shutil\.rmtree\s*\([^)]*["\']?/["\']?', "Blocked: shutil.rmtree() on root paths"),
    (r'shutil\.rmtree\s*\([^)]*["\']?~', "Blocked: shutil.rmtree() on home directory"),
]


def _validate_python_code(code: str) -> tuple[bool, str]:
    """Validate Python code against dangerous patterns."""
    if not code or not code.strip():
        return False, "Empty code not allowed"

    for pattern, message in DANGEROUS_PYTHON_PATTERNS:
        if re.search(pattern, code, re.IGNORECASE):
            return False, message

    return True, ""


class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search the internet for real-time information and trends."
    parameters = {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}

    async def execute(self, query: str) -> str:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
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
        # Preserve subdirectory structure - validation ensures it's within workspace
        filepath = os.path.join(self.workspace, filename) if not os.path.isabs(filename) else os.path.join(self.workspace, os.path.relpath(filename, "/"))
        # Ensure parent directories exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
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
        # Security: Validate command before execution
        is_valid, error_msg = _validate_terminal_command(command, self.workspace)
        if not is_valid:
            return f"SECURITY_ERROR: {error_msg}"

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

        # Security: Validate code before execution
        is_valid, error_msg = _validate_python_code(code)
        if not is_valid:
            return f"SECURITY_ERROR: {error_msg}"

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