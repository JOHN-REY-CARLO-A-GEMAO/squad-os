import json
import os
import asyncio
import socket
from typing import Optional, Dict, Any, List
from squad_os.tools.base import BaseTool


class SquadSyncManager:
    """Manages multi-device synchronization and mesh discovery."""

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.nodes: Dict[str, dict] = {}
        self.blackboard: Dict[str, str] = {}
        self._sync_url = os.environ.get("SQUAD_SYNC_URL", "http://localhost:8900")

    def register_node(self, node_id: str, host: str, port: int, capabilities: List[str] = None):
        self.nodes[node_id] = {
            "id": node_id,
            "host": host,
            "port": port,
            "capabilities": capabilities or [],
            "status": "online"
        }

    def get_capable_nodes(self, capability: str) -> List[dict]:
        return [
            n for n in self.nodes.values()
            if capability in n.get("capabilities", []) and n.get("status") == "online"
        ]


class SquadDiscoverTool(BaseTool):
    name = "squad_discover"
    description = (
        "Discover other SquadOS nodes on the local network via mDNS/ZeroConf "
        "or a configured sync server. Returns a list of available nodes and their capabilities. "
        "Use this to find devices that can share resources or offload tasks."
    )
    parameters = {
        "type": "object",
        "properties": {
            "timeout": {
                "type": "integer",
                "description": "Discovery timeout in seconds (default: 5)"
            }
        },
        "required": []
    }
    category = "sync"

    async def execute(self, timeout: int = 5) -> str:
        manager = SquadSyncManager.get_instance()
        import aiohttp

        sync_url = os.environ.get("SQUAD_SYNC_URL", "http://localhost:8900")
        discovered = []

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{sync_url}/nodes", timeout=timeout) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        discovered = data.get("nodes", [])
        except (aiohttp.ClientError, asyncio.TimeoutError):
            pass

        try:
            from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange
            from zeroconf import ServiceInfo
            zc = Zeroconf()
            discovered_services = []

            class Listener:
                def __init__(self):
                    self.services = []

                def add_service(self, zc, type_, name):
                    info = zc.get_service_info(type_, name)
                    if info:
                        self.services.append({
                            "name": name,
                            "host": socket.inet_ntoa(info.addresses[0]) if info.addresses else "unknown",
                            "port": info.port,
                            "server": info.server
                        })

            listener = Listener()
            browser = ServiceBrowser(zc, "_squados._tcp.local.", listener)
            await asyncio.sleep(timeout)
            zc.close()
            discovered_services = listener.services
            for svc in discovered_services:
                if svc not in discovered:
                    discovered.append(svc)
        except ImportError:
            pass
        except Exception:
            pass

        for node in discovered:
            nid = node.get("id") or node.get("name", "unknown")
            manager.register_node(
                nid,
                node.get("host", "unknown"),
                node.get("port", 0),
                node.get("capabilities", [])
            )

        return json.dumps({
            "nodes_found": len(discovered),
            "nodes": discovered or [{"message": "No nodes discovered. Is the sync server running?"}]
        }, indent=2)


class SquadBlackboardTool(BaseTool):
    name = "squad_blackboard"
    description = (
        "Access the shared blackboard across all SquadOS nodes. "
        "Use 'get' to read a value, 'set' to write, 'list' to see all keys, "
        "or 'subscribe' to watch for changes. Values are synced to all connected nodes."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["get", "set", "list", "delete"],
                "description": "Action to perform on the blackboard"
            },
            "key": {
                "type": "string",
                "description": "Blackboard key"
            },
            "value": {
                "type": "string",
                "description": "Value to store (for set action)"
            }
        },
        "required": ["action"]
    }
    category = "sync"

    async def execute(self, action: str, key: Optional[str] = None, value: Optional[str] = None) -> str:
        import aiohttp
        sync_url = os.environ.get("SQUAD_SYNC_URL", "http://localhost:8900")

        try:
            async with aiohttp.ClientSession() as session:
                if action == "get":
                    if not key:
                        return "Error: 'key' is required for get action."
                    async with session.get(f"{sync_url}/blackboard/{key}") as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return json.dumps(data, indent=2)
                        return f"Key '{key}' not found."

                elif action == "set":
                    if not key or value is None:
                        return "Error: 'key' and 'value' are required for set action."
                    async with session.post(f"{sync_url}/blackboard", json={"key": key, "value": value}) as resp:
                        if resp.status == 200:
                            return f"Blackboard '{key}' set successfully."
                        return f"Failed to set '{key}': {await resp.text()}"

                elif action == "list":
                    async with session.get(f"{sync_url}/blackboard") as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            keys = list(data.keys()) if isinstance(data, dict) else data
                            return json.dumps({"keys": keys}, indent=2)
                        return "No blackboard server available."

                elif action == "delete":
                    if not key:
                        return "Error: 'key' is required for delete action."
                    async with session.delete(f"{sync_url}/blackboard/{key}") as resp:
                        if resp.status == 200:
                            return f"Key '{key}' deleted."
                        return f"Failed to delete '{key}': {await resp.text()}"

                return f"Error: Unknown action '{action}'."
        except (aiohttp.ClientError, ImportError):
            # Fall back to local blackboard
            manager = SquadSyncManager.get_instance()
            if action == "get":
                val = manager.blackboard.get(key)
                return f"Value for '{key}': {val}" if val else f"Key '{key}' not found."
            elif action == "set":
                manager.blackboard[key] = value
                return f"Local blackboard '{key}' set."
            elif action == "list":
                return json.dumps({"keys": list(manager.blackboard.keys())}, indent=2)
            elif action == "delete":
                manager.blackboard.pop(key, None)
                return f"Key '{key}' deleted."
            return f"Error: No sync server at {sync_url}. Using local blackboard."


class SquadResourceTool(BaseTool):
    name = "squad_resources"
    description = (
        "Find nodes with specific computational resources (GPU, high-RAM, etc.) "
        "or advertise this node's resources to the mesh. "
        "Use this for distributed task allocation across devices."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["find", "advertise", "status"],
                "description": "'find' to search for capable nodes, 'advertise' to announce this node, 'status' to check mesh health"
            },
            "capability": {
                "type": "string",
                "description": "Required capability: 'gpu', 'high-memory', 'storage', 'browser', 'multimedia'"
            },
            "resources": {
                "type": "object",
                "description": "Resource spec for advertise action: { 'gpu': true, 'ram_gb': 32, 'cpu_cores': 8 }"
            }
        },
        "required": ["action"]
    }
    category = "sync"

    async def execute(self, action: str, capability: Optional[str] = None,
                      resources: Optional[Dict[str, Any]] = None) -> str:
        import aiohttp
        sync_url = os.environ.get("SQUAD_SYNC_URL", "http://localhost:8900")

        try:
            async with aiohttp.ClientSession() as session:
                if action == "find":
                    if not capability:
                        return "Error: 'capability' is required for find action."
                    async with session.get(f"{sync_url}/nodes?capability={capability}") as resp:
                        if resp.status == 200:
                            nodes = await resp.json()
                            cap_name = capability
                            capable = [n for n in nodes.get("nodes", []) if cap_name in n.get("capabilities", [])]
                            if not capable:
                                return f"No nodes found with '{cap_name}' capability."
                            return json.dumps({"capability": cap_name, "nodes": capable}, indent=2)
                        return f"Discovery server error: {resp.status}"

                elif action == "advertise":
                    if not resources:
                        return "Error: 'resources' are required for advertise."
                    payload = {
                        "id": socket.gethostname(),
                        "host": socket.gethostbyname(socket.gethostname()),
                        "port": int(os.environ.get("SQUAD_SYNC_PORT", "8901")),
                        "resources": resources,
                        "capabilities": [k for k, v in (resources or {}).items() if v is True]
                    }
                    async with session.post(f"{sync_url}/nodes", json=payload) as resp:
                        if resp.status == 200:
                            return f"Node advertised successfully: {json.dumps(payload, indent=2)}"
                        return f"Failed to advertise: {await resp.text()}"

                elif action == "status":
                    async with session.get(f"{sync_url}/health") as resp:
                        if resp.status == 200:
                            return await resp.text()
                        return f"Mesh health check failed: {resp.status}"

                return f"Error: Unknown action '{action}'."
        except (aiohttp.ClientError, ImportError) as e:
            # Local fallback - return self
            try:
                import psutil
                mem = psutil.virtual_memory()
                cpu = psutil.cpu_count()
                return json.dumps({
                    "message": "No sync server. Reporting local resources only.",
                    "local_node": {
                        "hostname": socket.gethostname(),
                        "cpu_cores": cpu,
                        "ram_gb": round(mem.total / (1024**3), 1),
                        "ram_free_gb": round(mem.available / (1024**3), 1)
                    }
                }, indent=2)
            except ImportError:
                return json.dumps({
                    "message": "No sync server. Install 'psutil' for detailed local reporting.",
                    "local_node": {"hostname": socket.gethostname()}
                }, indent=2)
