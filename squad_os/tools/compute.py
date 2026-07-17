import json
import os
import asyncio
import socket
from typing import Optional, List, Dict, Any
from squad_os.tools.base import BaseTool, retry_on_failure


class ComputeDelegateTool(BaseTool):
    name = "compute_delegate"
    description = (
        "Delegate heavy computation tasks (video rendering, model training, 4K upscaling) "
        "to remote GPU-enabled nodes on the network. The task is transferred as a package, "
        "executed remotely, and results are returned. Works with SquadSync for node discovery."
    )
    parameters = {
        "type": "object",
        "properties": {
            "task_type": {
                "type": "string",
                "enum": ["video_gen", "image_gen", "training", "inference"],
                "description": "Type of computation to delegate"
            },
            "payload": {
                "type": "object",
                "description": "Task payload with parameters for the remote execution"
            },
            "target_node": {
                "type": "string",
                "description": "Specific node ID to target (optional, auto-selects best node if omitted)"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 300)"
            },
            "wait_for_result": {
                "type": "boolean",
                "description": "Whether to wait synchronously for the result (default: true)"
            }
        },
        "required": ["task_type", "payload"]
    }
    category = "compute"

    @retry_on_failure(max_attempts=2, delay=2.0)
    async def execute(self, task_type: str, payload: Dict[str, Any],
                      target_node: Optional[str] = None, timeout: int = 300,
                      wait_for_result: bool = True) -> str:
        import aiohttp
        sync_url = os.environ.get("SQUAD_SYNC_URL", "http://localhost:8900")

        node_host = None
        node_port = None

        if target_node:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{sync_url}/nodes/{target_node}") as resp:
                        if resp.status == 200:
                            info = await resp.json()
                            node_host = info.get("host")
                            node_port = info.get("port", 8901)
            except Exception:
                pass
            if not node_host:
                return f"Target node '{target_node}' not found or unreachable."

        task_package = {
            "task_id": f"{socket.gethostname()}_{asyncio.get_event_loop().time()}",
            "type": task_type,
            "payload": payload,
            "source": socket.gethostname(),
            "callback_url": f"http://{socket.gethostbyname(socket.gethostname())}:{os.environ.get('SQUAD_SYNC_PORT', '8901')}/callback"
        }

        if node_host:
            delegate_url = f"http://{node_host}:{node_port}/execute"
        else:
            delegate_url = f"{sync_url}/delegate"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(delegate_url, json=task_package, timeout=timeout) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return json.dumps({
                            "status": "completed" if wait_for_result else "dispatched",
                            "node": target_node or "auto-selected",
                            "task_type": task_type,
                            "result": result.get("result", result),
                            "task_id": task_package["task_id"]
                        }, indent=2)

                    if resp.status == 202:
                        task_info = await resp.json()
                        return json.dumps({
                            "status": "dispatched",
                            "task_id": task_info.get("task_id", task_package["task_id"]),
                            "message": "Task accepted for async execution. Check status with compute_status.",
                            "node": target_node or "auto-selected"
                        }, indent=2)

                    return f"Delegation failed: {resp.status} - {await resp.text()}"
        except (aiohttp.ClientError, ImportError) as e:
            return f"Offload failed: {e}. Ensure the compute server is running."


class ComputeStatusTool(BaseTool):
    name = "compute_status"
    description = (
        "Check the status of offloaded computation tasks. "
        "Returns progress, completion status, and results for delegated tasks."
    )
    parameters = {
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "Task ID to check (returns all tasks if omitted)"
            }
        },
        "required": []
    }
    category = "compute"

    async def execute(self, task_id: Optional[str] = None) -> str:
        import aiohttp
        sync_url = os.environ.get("SQUAD_SYNC_URL", "http://localhost:8900")

        try:
            async with aiohttp.ClientSession() as session:
                endpoint = f"{sync_url}/tasks/{task_id}" if task_id else f"{sync_url}/tasks"
                async with session.get(endpoint) as resp:
                    if resp.status == 200:
                        return await resp.text()
                    return f"No task info available: {resp.status}"
        except (aiohttp.ClientError, ImportError):
            return "No compute server available. Task tracking requires a SquadSync server."


class GPUInfoTool(BaseTool):
    name = "gpu_info"
    description = (
        "Query GPU hardware information: model, VRAM, CUDA cores, temperature, utilization. "
        "Use this to check if GPU offload is viable or to diagnose hardware acceleration."
    )
    parameters = {
        "type": "object",
        "properties": {
            "detailed": {
                "type": "boolean",
                "description": "Return detailed per-GPU metrics (default: false)"
            }
        },
        "required": []
    }
    category = "compute"

    async def execute(self, detailed: bool = False) -> str:
        info = {"gpus": []}

        try:
            import torch
            if torch.cuda.is_available():
                for i in range(torch.cuda.device_count()):
                    props = torch.cuda.get_device_properties(i)
                    gpu = {
                        "index": i,
                        "name": props.name,
                        "total_vram_gb": round(props.total_memory / (1024**3), 2),
                        "compute_capability": f"{props.major}.{props.minor}",
                        "multi_processor_count": props.multi_processor_count
                    }
                    if detailed:
                        gpu["allocated_vram_gb"] = round(torch.cuda.memory_allocated(i) / (1024**3), 2)
                        gpu["cached_vram_gb"] = round(torch.cuda.memory_reserved(i) / (1024**3), 2)
                        gpu["utilization"] = f"{torch.cuda.utilization(i)}%" if hasattr(torch.cuda, 'utilization') else "N/A"
                    info["gpus"].append(gpu)
                info["cuda_available"] = True
                info["cuda_version"] = torch.version.cuda
            else:
                info["cuda_available"] = False
                info["message"] = "No CUDA-capable GPU detected."
        except ImportError:
            info["message"] = "PyTorch not installed. Install with: pip install torch"

        if not info["gpus"]:
            try:
                import subprocess
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split("\n")
                    for i, line in enumerate(lines):
                        parts = [p.strip() for p in line.split(",")]
                        if len(parts) >= 2:
                            info["gpus"].append({
                                "index": i,
                                "name": parts[0],
                                "vram": parts[1],
                                "driver": parts[2] if len(parts) > 2 else "unknown",
                                "source": "nvidia-smi"
                            })
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

        if not info["gpus"]:
            info["message"] = "No GPU detected via PyTorch or nvidia-smi."

        return json.dumps(info, indent=2)
