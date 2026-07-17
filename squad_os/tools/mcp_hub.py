import asyncio
import json
import os
from typing import Optional, List, Dict, Any
from squad_os.tools.base import BaseTool, retry_on_failure

MCP_SERVERS_CONFIG_PATH = os.path.join("workspace", "mcp_servers.json")


class MCPConnectionError(Exception):
    pass


class MCPConnection:
    """Long-lived stdio connection to an MCP server using Content-Length framing.

    Manages a single subprocess with persistent stdin/stdout pipes.
    Messages use the standard MCP transport framing:
        Content-Length: <N>\\r\\n\\r\\n<JSON body>
    """

    def __init__(self, name: str, command: str, args: List[str] = None,
                 env: Dict[str, str] = None):
        self.name = name
        self.command = command
        self.args = args or []
        merged_env = dict(os.environ)
        if env:
            merged_env.update(env)
        self.env = merged_env
        self.process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0
        self._lock = asyncio.Lock()
        self._reader_task: Optional[asyncio.Task] = None
        self._stderr_task: Optional[asyncio.Task] = None
        self._pending: Dict[int, asyncio.Future] = {}
        self._read_buffer = b""
        self.connected = False
        self._closing = False

    async def connect(self):
        """Spawn the subprocess and begin reading stdout/stderr."""
        self._closing = False
        self.process = await asyncio.create_subprocess_exec(
            self.command, *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.env,
        )
        self.connected = True
        self._reader_task = asyncio.create_task(self._read_loop())
        self._stderr_task = asyncio.create_task(self._drain_stderr())

    async def _read_loop(self):
        """Continuously read stdout and dispatch completed JSON-RPC messages."""
        while self.connected and self.process and self.process.stdout:
            try:
                chunk = await self.process.stdout.read(65536)
                if not chunk:
                    break
                self._read_buffer += chunk
                await self._dispatch_messages()
            except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
                break
        self.connected = False

    async def _dispatch_messages(self):
        """Extract and route all complete messages from the read buffer."""
        while True:
            header_end = self._read_buffer.find(b"\r\n\r\n")
            if header_end == -1:
                return

            header_bytes = self._read_buffer[:header_end]
            content_length = 0
            for line in header_bytes.decode("utf-8", errors="replace").split("\r\n"):
                if line.lower().startswith("content-length:"):
                    try:
                        content_length = int(line.split(":", 1)[1].strip())
                    except ValueError:
                        pass

            if content_length <= 0:
                self._read_buffer = self._read_buffer[header_end + 4:]
                continue

            body_start = header_end + 4
            body_end = body_start + content_length
            if len(self._read_buffer) < body_end:
                return

            body = self._read_buffer[body_start:body_end]
            self._read_buffer = self._read_buffer[body_end:]

            try:
                msg = json.loads(body.decode("utf-8"))
                req_id = msg.get("id")
                if req_id is not None and req_id in self._pending:
                    future = self._pending.pop(req_id)
                    if not future.done():
                        future.set_result(msg)
            except json.JSONDecodeError:
                pass

    async def _drain_stderr(self):
        """Drain stderr to prevent pipe buffer deadlock on Windows."""
        while self.process and self.process.stderr:
            try:
                chunk = await self.process.stderr.read(65536)
                if not chunk:
                    break
            except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
                break

    async def request(self, method: str, params: Dict[str, Any] = None,
                      timeout: float = 30.0) -> Dict[str, Any]:
        """Send a JSON-RPC request and await the response."""
        async with self._lock:
            if not self.connected or not self.process or not self.process.stdin:
                raise MCPConnectionError(f"Connection to '{self.name}' is not open")

            self._request_id += 1
            req_id = self._request_id
            payload = json.dumps({
                "jsonrpc": "2.0",
                "method": method,
                "params": params or {},
                "id": req_id,
            })
            frame = f"Content-Length: {len(payload.encode())}\r\n\r\n{payload}".encode()
            self.process.stdin.write(frame)
            await self.process.stdin.drain()

            future = asyncio.get_event_loop().create_future()
            self._pending[req_id] = future

        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            if "error" in response:
                err = response["error"]
                raise MCPConnectionError(err.get("message", "Unknown MCP error"))
            return response.get("result", {})
        except asyncio.TimeoutError:
            self._pending.pop(req_id, None)
            raise MCPConnectionError(f"Request '{method}' timed out after {timeout}s")

    async def reconnect(self):
        """Close the current connection and open a fresh one."""
        await self.close()
        await self.connect()

    async def close(self):
        """Gracefully shut down the subprocess and cancel pending futures."""
        self._closing = True
        self.connected = False

        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass

        if self._stderr_task:
            self._stderr_task.cancel()
            try:
                await self._stderr_task
            except asyncio.CancelledError:
                pass

        for future in self._pending.values():
            if not future.done():
                future.set_exception(asyncio.CancelledError())
        self._pending.clear()

        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
            except Exception:
                pass
            self.process = None


class ConnectionPool:
    """Manages lifecycle of multiple MCP server connections with auto-reconnect."""

    def __init__(self):
        self._connections: Dict[str, MCPConnection] = {}
        self._configs: Dict[str, dict] = {}

    def register(self, name: str, command: str, args: List[str] = None,
                 env: Dict[str, str] = None):
        self._configs[name] = {
            "command": command,
            "args": args or [],
            "env": env or {},
        }

    def unregister(self, name: str):
        self._configs.pop(name, None)

    async def connect(self, name: str) -> MCPConnection:
        if name in self._connections:
            existing = self._connections[name]
            if existing.connected:
                return existing
            await existing.close()

        cfg = self._configs.get(name)
        if not cfg:
            raise MCPConnectionError(f"Server '{name}' is not registered")
        conn = MCPConnection(name, cfg["command"], cfg["args"], cfg["env"])
        await conn.connect()
        self._connections[name] = conn
        return conn

    async def get(self, name: str) -> MCPConnection:
        if name in self._connections:
            conn = self._connections[name]
            if conn.connected:
                return conn
            print(f"  [ConnectionPool] '{name}' disconnected — reconnecting...")
            await conn.close()
        return await self.connect(name)

    async def disconnect(self, name: str):
        conn = self._connections.pop(name, None)
        if conn:
            await conn.close()

    async def disconnect_all(self):
        for conn in list(self._connections.values()):
            await conn.close()
        self._connections.clear()

    @property
    def active_names(self) -> List[str]:
        return list(self._connections.keys())

    @property
    def registered_names(self) -> List[str]:
        return list(self._configs.keys())


class MCPAggregator:
    """Singleton — the central gateway to all MCP servers.

    - Loads registered servers from workspace/mcp_servers.json
    - Manages long-lived connections via ConnectionPool
    - Discovers and caches tool schemas via tools/list
    - Provides a unified call_tool interface
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.pool = ConnectionPool()
        self._tool_cache: Dict[str, List[dict]] = {}
        self._servers: Dict[str, dict] = {}
        self._load_config()

    def _load_config(self):
        if not os.path.exists(MCP_SERVERS_CONFIG_PATH):
            return
        try:
            with open(MCP_SERVERS_CONFIG_PATH) as f:
                cfg = json.load(f)
            for server in cfg.get("mcp_servers", []):
                name = server["name"]
                self._servers[name] = server
                if server.get("transport") == "stdio":
                    self.pool.register(
                        name,
                        server["command"],
                        server.get("args", []),
                        server.get("env", {}),
                    )
        except (json.JSONDecodeError, KeyError):
            pass

    def _persist_config(self):
        os.makedirs(os.path.dirname(MCP_SERVERS_CONFIG_PATH), exist_ok=True)
        with open(MCP_SERVERS_CONFIG_PATH, "w") as f:
            json.dump({"mcp_servers": list(self._servers.values())}, f, indent=2)

    def register_server(self, name: str, command: str, args: List[str] = None,
                        env: Dict[str, str] = None):
        self._servers[name] = {
            "name": name,
            "transport": "stdio",
            "command": command,
            "args": args or [],
            "env": env or {},
        }
        self.pool.register(name, command, args, env)
        self._persist_config()

    def register_sse_server(self, name: str, url: str):
        self._servers[name] = {
            "name": name,
            "transport": "sse",
            "url": url,
        }
        self._persist_config()

    async def discover_tools(self, server: str) -> List[dict]:
        """Connect to a server, call tools/list, and cache the result."""
        conn = await self.pool.get(server)
        result = await conn.request("tools/list")
        tools = result.get("tools", [])
        self._tool_cache[server] = tools
        return tools

    async def discover_all(self) -> Dict[str, List[dict]]:
        """Discover tools from every registered stdio server."""
        for name in list(self._servers.keys()):
            if self._servers[name].get("transport") != "stdio":
                continue
            try:
                await self.discover_tools(name)
            except MCPConnectionError as e:
                print(f"  [MCPAggregator] Could not connect to '{name}': {e}")
                self._tool_cache.setdefault(name, [])
        return self._tool_cache

    async def call_tool(self, server: str, tool: str,
                        arguments: Dict[str, Any] = None) -> str:
        conn = await self.pool.get(server)
        result = await conn.request("tools/call", {"name": tool, "arguments": arguments or {}})
        content = result.get("content", [])
        return "\n".join(
            c.get("text", json.dumps(c)) for c in content if isinstance(c, dict)
        ) or json.dumps(result, indent=2)

    def get_cached_tools(self, server: str) -> List[dict]:
        return self._tool_cache.get(server, [])

    def get_server_info(self, name: str) -> Optional[dict]:
        return self._servers.get(name)

    def list_servers(self) -> List[str]:
        return list(self._servers.keys())

    def inject_native_tools(self):
        """Build and register native BaseTool instances from all cached schemas."""
        try:
            from squad_os.tools.marketplace import SkillRegistry
            reg = SkillRegistry.get_instance()
            for server in self.list_servers():
                for schema in self.get_cached_tools(server):
                    try:
                        tool_class = create_mcp_native_tool(server, schema)
                        reg.register_dynamic(tool_class)
                    except Exception as e:
                        print(f"  [MCP] Failed to create native tool {server}/{schema.get('name')}: {e}")
        except ImportError:
            pass

    async def shutdown(self):
        await self.pool.disconnect_all()
        self._tool_cache.clear()


def _slugify(name: str) -> str:
    return name.lower().replace("-", "_").replace(" ", "_").replace("/", "_")


def _make_mcp_execute(server: str, tool_name: str):
    """Closure factory: captures server + tool_name for a dynamic tool's execute()."""
    async def execute(self, **kwargs) -> str:
        agg = MCPAggregator.get_instance()
        try:
            return await agg.call_tool(server, tool_name, kwargs)
        except MCPConnectionError as e:
            return f"MCP error: {e}"
        except Exception as e:
            return f"MCP error: {str(e)}"
    execute.__qualname__ = f"MCPNative_{_slugify(server)}_{tool_name}.execute"
    return execute


def create_mcp_native_tool(server: str, tool_schema: dict) -> type:
    """Dynamically create a BaseTool subclass from an MCP tool schema.

    The generated tool's name is namespaced as ``{server}_{tool_name}`` so
    it won't collide with built-in tools.  Its ``execute()`` routes through
    ``MCPAggregator.call_tool()`` — the MCP layer is invisible to the agent.
    """
    raw_name = tool_schema["name"]
    namespaced_name = f"{_slugify(server)}_{raw_name}"
    raw_schema = tool_schema.get("inputSchema")
    input_schema = raw_schema if isinstance(raw_schema, dict) else {"type": "object", "properties": {}}
    description = tool_schema.get(
        "description",
        f"Call '{raw_name}' on the MCP server '{server}'.",
    )

    cls = type(
        f"MCPNative_{namespaced_name}",
        (BaseTool,),
        {
            "name": namespaced_name,
            "description": description,
            "parameters": input_schema,
            "category": "mcp",
            "_mcp_server": server,
            "_mcp_tool": raw_name,
            "execute": _make_mcp_execute(server, raw_name),
        },
    )
    return cls


class MCPWrapperTool(BaseTool):
    name = "mcp_call"
    description = (
        "Execute a tool on a connected MCP server. "
        "MCP (Model Context Protocol) provides access to external tools like Brave Search, "
        "GitHub, Postgres, and more. Use mcp_list first to discover available servers and tools."
    )
    parameters = {
        "type": "object",
        "properties": {
            "server": {
                "type": "string",
                "description": "Name of the MCP server to call"
            },
            "tool": {
                "type": "string",
                "description": "Name of the tool to execute on the server"
            },
            "arguments": {
                "type": "object",
                "description": "Arguments to pass to the tool"
            }
        },
        "required": ["server", "tool"]
    }
    category = "connectivity"

    @retry_on_failure(max_attempts=2, delay=1.0)
    async def execute(self, server: str, tool: str,
                      arguments: Optional[Dict[str, Any]] = None) -> str:
        agg = MCPAggregator.get_instance()
        if server not in agg._servers:
            available = agg.list_servers()
            return f"Server '{server}' not found. Available: {available}"
        try:
            return await agg.call_tool(server, tool, arguments)
        except MCPConnectionError as e:
            return f"MCP call failed: {e}"
        except Exception as e:
            return f"MCP call failed: {str(e)}"


class MCPListTool(BaseTool):
    name = "mcp_list"
    description = (
        "List all registered MCP servers and their available tools. "
        "Use this to discover what external capabilities are available via MCP."
    )
    parameters = {
        "type": "object",
        "properties": {
            "server": {
                "type": "string",
                "description": "Optional server name to list tools for a specific server"
            }
        },
        "required": []
    }
    category = "connectivity"

    async def execute(self, server: Optional[str] = None) -> str:
        agg = MCPAggregator.get_instance()
        if server:
            info = agg.get_server_info(server)
            if not info:
                return f"Server '{server}' not found. Available: {agg.list_servers()}"
            tools = agg.get_cached_tools(server)
            if tools:
                return json.dumps({"server": server, "transport": info.get("transport", "unknown"),
                                   "tools_count": len(tools), "tools": tools}, indent=2)
            return json.dumps({"server": server, "transport": info.get("transport", "unknown"),
                               "status": "registered"}, indent=2)

        servers = agg.list_servers()
        if not servers:
            return "No MCP servers registered. Use mcp_register to add one."
        details = []
        for name in servers:
            info = agg.get_server_info(name)
            tools = agg.get_cached_tools(name)
            entry = {"name": name, "transport": info.get("transport", "unknown")}
            if tools:
                entry["tools_count"] = len(tools)
            details.append(entry)
        return json.dumps({"mcp_servers": details}, indent=2)


class MCPRegisterTool(BaseTool):
    name = "mcp_register"
    description = (
        "Register a new MCP server connection. Supports stdio (local subprocess) "
        "and SSE (HTTP) transports. After registration, tools on that server become "
        "available via mcp_call."
    )
    parameters = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Unique name for this MCP server"
            },
            "transport": {
                "type": "string",
                "enum": ["stdio", "sse"],
                "description": "Transport type: 'stdio' for local subprocess, 'sse' for HTTP endpoint"
            },
            "command": {
                "type": "string",
                "description": "Command to start the server (for stdio transport)"
            },
            "args": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Command-line arguments (for stdio transport)"
            },
            "url": {
                "type": "string",
                "description": "SSE endpoint URL (for sse transport)"
            },
            "env": {
                "type": "object",
                "description": "Environment variables for the server process"
            }
        },
        "required": ["name", "transport"]
    }
    category = "connectivity"

    async def execute(self, name: str, transport: str, command: Optional[str] = None,
                      args: Optional[List[str]] = None, url: Optional[str] = None,
                      env: Optional[Dict[str, str]] = None) -> str:
        agg = MCPAggregator.get_instance()
        if transport == "stdio":
            if not command:
                return "Error: 'command' is required for stdio transport."
            agg.register_server(name, command, args, env)
            return (f"MCP server '{name}' registered ({transport}). "
                    "Use mcp_list to verify or mcp_discover to load its tools.")
        elif transport == "sse":
            if not url:
                return "Error: 'url' is required for sse transport."
            agg.register_sse_server(name, url)
            return f"MCP server '{name}' registered ({transport}, {url})"
        return f"Error: Unknown transport '{transport}'."


class MCPDiscoverTool(BaseTool):
    name = "mcp_discover"
    description = (
        "Connect to a registered MCP server and discover its available tools. "
        "Caches the tool schemas so future calls have full metadata."
    )
    parameters = {
        "type": "object",
        "properties": {
            "server": {
                "type": "string",
                "description": "Name of the MCP server to discover tools on"
            }
        },
        "required": ["server"]
    }
    category = "connectivity"

    async def execute(self, server: str) -> str:
        agg = MCPAggregator.get_instance()
        if server not in agg._servers:
            return f"Server '{server}' not found. Available: {agg.list_servers()}"
        try:
            tools = await agg.discover_tools(server)
            agg.inject_native_tools()
            return json.dumps({
                "server": server,
                "tools_count": len(tools),
                "tools": tools,
            }, indent=2)
        except MCPConnectionError as e:
            return f"Discovery failed: {e}"
        except Exception as e:
            return f"Discovery failed: {str(e)}"
