import os
import subprocess
import asyncio
import json
import re
import shlex
from typing import Dict, Any, Optional, List, Set

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

from squad_os.tools.base import BaseTool
from squad_os.core.utils import is_safe_path

# Security: Dangerous regex patterns for terminal commands
DANGEROUS_REGEX_PATTERNS: Set[str] = {
    r'rm\s+-rf\s+/', r'rm\s+-rf\s+/\*', r'rm\s+-rf\s+~', r'dd\s+if=/dev/zero', r'mkfs\.', r'fdisk',
    r'>:', r'>&', r'/dev/null', r'shutdown', r'reboot', r'halt', r'poweroff',
    r'init\s+0', r'telinit\s+0', r'kill\s+-9\s+-1', r'kill\s+-9\s+1',
    r'curl\s+.*\|\s*.*sh', r'curl\s+.*\|\s*.*bash', r'wget\s+.*\|\s*.*sh', r'wget\s+.*\|\s*.*bash',
    r'>\s+/etc/', r'>>\s+/etc/', r'echo.*>\s+/', r'echo.*>>\s+/',
    r'chmod\s+777\s+/', r'chmod\s+-R\s+777\s+/', r'chown\s+-R',
    r'mkfs\.ext', r'mkfs\.btrfs', r'mkfs\.xfs', r'parted', r'gparted',
    r'del\s+/f\s+/s\s+/q', r'rd\s+/s\s+/q', r'format\s+', r'diskpart',
}

# Trusted system directories for absolute command paths
TRUSTED_SYSTEM_DIRS: Set[str] = {"/bin/", "/usr/bin/", "/usr/local/bin/"}

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
    """Check if command contains dangerous patterns using regex."""
    cmd_lower = command.lower().strip()
    for pattern in DANGEROUS_REGEX_PATTERNS:
        if re.search(pattern, cmd_lower):
            return True
    # Check for shell injection patterns
    if re.search(r'`[^`]+`', cmd_lower) or re.search(r'\$\([^)]+\)', cmd_lower):
        return True
    return False


def _looks_like_path(token: str) -> bool:
    """Check if a token looks like a file/directory path rather than a command flag."""
    # Command flags start with / or - and contain only alphanumeric chars
    # Examples: /s, /b, -la, --verbose, -rf
    if token.startswith('/') or token.startswith('-'):
        # Windows flags: /s, /b, /q, etc. (single char after /)
        # Unix flags: -la, --verbose, -rf (letters after - or --)
        stripped = token.lstrip('/-')
        if stripped.isalnum():
            return False  # It's a flag, not a path
    
    # Tokens that look like paths:
    # - Contain directory separators (/, \)
    # - Start with . (., .., ./file)
    # - Contain file extensions (.py, .txt)
    # - Contain .. (path traversal attempt)
    if any(c in token for c in ['/', '\\', '..']):
        return True
    if token.startswith('.'):
        return True
    if '.' in token and len(token.split('.')) > 1:
        return True
    
    return False


def _validate_terminal_command(command: str, workspace: str) -> tuple[bool, str]:
    """Validate terminal command against allowlist and dangerous patterns."""
    if not command or not command.strip():
        return False, "Empty command not allowed"

    if _is_dangerous_command(command):
        return False, "Command contains dangerous patterns and is blocked for security"

    # Define operators
    COMMAND_OPERATORS = {';', '&&', '||', '|', '&'}
    # Standard redirection operators
    REDIRECT_OPERATORS = {'>', '<', '>>', '<<', '>&', '<&'}

    # Parse command using shlex with punctuation support
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
        if not tokens:
            return False, "Could not parse command"
    except ValueError as e:
        return False, f"Command parsing error: {str(e)}"

    expect_command = True
    for token in tokens:
        # Check for command operators that start a new command context
        if token in COMMAND_OPERATORS:
            expect_command = True
            continue

        # Redirection operators themselves are safe, but they switch off expect_command
        if token in REDIRECT_OPERATORS:
            expect_command = False
            continue

        # If we expect a command name (at start or after an operator)
        if expect_command:
            cmd_name = token.lower()
            # Allow common shell built-ins and safe commands
            if cmd_name in ALLOWED_COMMANDS:
                # OK - allowed built-in or registered command
                pass
            elif cmd_name.startswith('./'):
                # Local execution - MUST check if it's within workspace
                if not is_safe_path(workspace, cmd_name):
                    return False, f"Access denied: Command '{cmd_name}' attempts to execute outside workspace"
            elif cmd_name.startswith('/'):
                # Absolute path execution - restrict to trusted system directories
                parent_dir = os.path.dirname(cmd_name)
                if not parent_dir.endswith('/'):
                    parent_dir += '/'

                if parent_dir not in TRUSTED_SYSTEM_DIRS:
                    return False, f"Security violation: Command '{cmd_name}' is from an untrusted directory"

                if os.path.basename(cmd_name) not in ALLOWED_COMMANDS:
                    return False, f"Command '{cmd_name}' not in allowed list"
            elif '/' in cmd_name or '\\' in cmd_name:
                # Other qualified paths (e.g., relative paths with separators)
                if not is_safe_path(workspace, cmd_name):
                    return False, f"Access denied: Command '{cmd_name}' attempts to execute outside workspace"
                if os.path.basename(cmd_name) not in ALLOWED_COMMANDS:
                    return False, f"Command '{cmd_name}' not in allowed list"
            else:
                return False, f"Command '{cmd_name}' not in allowed list"

            expect_command = False
            continue

        # Path Traversal Check: Only check tokens that look like actual paths
        # Skip command flags (e.g., /s, /b, -la, --verbose) and simple arguments
        if _looks_like_path(token) and not is_safe_path(workspace, token):
            return False, f"Access denied: Token '{token}' attempts to access path outside workspace"

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
        # Security enhancement: Input validation and sanitization
        query = query.strip()
        if not query:
            return "Error: Empty search query."

        # Prevent DoS/abuse by limiting query length
        MAX_QUERY_LENGTH = 200
        if len(query) > MAX_QUERY_LENGTH:
            query = query[:MAX_QUERY_LENGTH]

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


def _translate_unix_to_windows(command: str) -> str:
    """Translate common Unix commands to Windows PowerShell equivalents."""
    import re
    
    # Handle mkdir -p (create parent directories)
    # Unix: mkdir -p project/src project/tests
    # Windows: New-Item -ItemType Directory -Force -Path "project\src", "project\tests"
    mkdir_p_match = re.match(r'mkdir\s+-p\s+(.+)', command)
    if mkdir_p_match:
        paths = mkdir_p_match.group(1).strip()
        # Split by spaces but respect quoted paths
        path_list = [p.strip() for p in re.split(r'\s+(?![^"]*"(?:\s+[^"]*")*$)', paths)]
        # Convert forward slashes to backslashes for Windows
        path_list = [p.replace('/', '\\') for p in path_list]
        paths_str = ', '.join([f'"{p}"' for p in path_list])
        return f'New-Item -ItemType Directory -Force -Path {paths_str}'
    
    # Handle touch (create empty files)
    # Unix: touch file1.txt file2.txt
    # Windows: New-Item -ItemType File -Force -Path "file1.txt", "file2.txt"
    touch_match = re.match(r'touch\s+(.+)', command)
    if touch_match:
        files = touch_match.group(1).strip()
        file_list = [f.strip() for f in re.split(r'\s+(?![^"]*"(?:\s+[^"]*")*$)', files)]
        file_list = [f.replace('/', '\\') for f in file_list]
        files_str = ', '.join([f'"{f}"' for f in file_list])
        return f'New-Item -ItemType File -Force -Path {files_str}'
    
    # Handle ls (list directory contents)
    # Unix: ls -la
    # Windows: Get-ChildItem -Force
    ls_match = re.match(r'ls(?:\s+\S+)?', command)
    if ls_match:
        return 'Get-ChildItem -Force'
    
    # Handle rm -rf (remove recursively)
    # Unix: rm -rf folder
    # Windows: Remove-Item -Recurse -Force -Path "folder"
    rm_rf_match = re.match(r'rm\s+-rf\s+(.+)', command)
    if rm_rf_match:
        path = rm_rf_match.group(1).strip().replace('/', '\\')
        return f'Remove-Item -Recurse -Force -Path "{path}"'
    
    # Handle cat (display file contents)
    # Unix: cat file.txt
    # Windows: Get-Content -Path "file.txt"
    cat_match = re.match(r'cat\s+(.+)', command)
    if cat_match:
        path = cat_match.group(1).strip().replace('/', '\\')
        return f'Get-Content -Path "{path}"'
    
    # Handle cp (copy files)
    # Unix: cp source dest
    # Windows: Copy-Item -Path "source" -Destination "dest"
    cp_match = re.match(r'cp\s+(\S+)\s+(\S+)', command)
    if cp_match:
        src = cp_match.group(1).replace('/', '\\')
        dest = cp_match.group(2).replace('/', '\\')
        return f'Copy-Item -Path "{src}" -Destination "{dest}"'
    
    # Handle mv (move files)
    # Unix: mv source dest
    # Windows: Move-Item -Path "source" -Destination "dest"
    mv_match = re.match(r'mv\s+(\S+)\s+(\S+)', command)
    if mv_match:
        src = mv_match.group(1).replace('/', '\\')
        dest = mv_match.group(2).replace('/', '\\')
        return f'Move-Item -Path "{src}" -Destination "{dest}"'
    
    # Handle pwd (print working directory)
    if command.strip() == 'pwd':
        return 'Get-Location'
    
    # Handle echo
    # Unix: echo "text" > file.txt
    # Windows: Set-Content -Path "file.txt" -Value "text"
    echo_redirect_match = re.match(r'echo\s+"([^"]+)"\s*>\s*(\S+)', command)
    if echo_redirect_match:
        text = echo_redirect_match.group(1)
        path = echo_redirect_match.group(2).replace('/', '\\')
        return f'Set-Content -Path "{path}" -Value "{text}"'
    
    return command


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

        # Cross-platform compatibility: Translate Unix commands to Windows equivalents
        if os.name == 'nt':  # Windows
            command = _translate_unix_to_windows(command)

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
            model_name="ollama/glm-4.7"
        )
        result = await sub_agent.execute_task(task_description, "Context: Working as a specialist.")
        output = result.get("output") or "No output returned."
        return f"DELEGATED RESULT FROM {specialist_role}: {output}"