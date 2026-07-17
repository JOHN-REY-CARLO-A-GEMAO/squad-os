import os
import json
import asyncio
from typing import Optional
from squad_os.tools.base import BaseTool


class SystemMonitorTool(BaseTool):
    name = "system_monitor"
    description = (
        "Monitor system resources: CPU load, memory usage, temperature, disk I/O, and process health. "
        "Provides real-time metrics for resource-aware task scheduling. "
        "Use this to check if the system can handle more tasks before launching heavy operations."
    )
    parameters = {
        "type": "object",
        "properties": {
            "metric": {
                "type": "string",
                "enum": ["all", "cpu", "memory", "temperature", "disk", "processes"],
                "description": "Which metric to check (default: 'all')"
            },
            "alert_threshold": {
                "type": "boolean",
                "description": "Return only alerts/threshold violations (default: false)"
            }
        },
        "required": []
    }
    category = "system"
    workspace = None  # injected by BaseAgent at runtime

    async def execute(self, metric: str = "all", alert_threshold: bool = False) -> str:
        try:
            import psutil
        except ImportError:
            return "Error: 'psutil' is required. Install with: pip install psutil"

        data = {}

        if metric in ("all", "cpu"):
            cpu_percent = psutil.cpu_percent(interval=0.5, percpu=True)
            cpu_freq = psutil.cpu_freq()
            data["cpu"] = {
                "percent_per_core": cpu_percent,
                "average": round(sum(cpu_percent) / len(cpu_percent), 1),
                "cores": len(cpu_percent),
                "frequency_mhz": round(cpu_freq.current, 1) if cpu_freq else None
            }

        if metric in ("all", "memory"):
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            data["memory"] = {
                "total_gb": round(mem.total / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "used_gb": round(mem.used / (1024**3), 2),
                "percent": mem.percent,
                "swap_total_gb": round(swap.total / (1024**3), 2) if swap.total > 0 else 0,
                "swap_percent": swap.percent
            }

        if metric in ("all", "temperature"):
            try:
                temps = psutil.sensors_temperatures()
                data["temperature"] = {}
                for name, entries in temps.items():
                    data["temperature"][name] = [
                        {"label": e.label or name, "current": e.current, "high": e.high, "critical": e.critical}
                        for e in entries
                    ]
            except Exception:
                data["temperature"] = {"status": "not available on this system"}

        if metric in ("all", "disk"):
            disks = []
            for part in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    disks.append({
                        "device": part.device,
                        "mount": part.mountpoint,
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "free_gb": round(usage.free / (1024**3), 2),
                        "percent": usage.percent
                    })
                except PermissionError:
                    continue
            data["disk"] = disks
            io = psutil.disk_io_counters()
            if io:
                data["disk_io"] = {
                    "read_mb": round(io.read_bytes / (1024**2), 2),
                    "write_mb": round(io.write_bytes / (1024**2), 2)
                }

        if metric in ("all", "processes"):
            procs = []
            for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
                try:
                    procs.append(p.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            procs.sort(key=lambda x: x.get("cpu_percent", 0) or 0, reverse=True)
            data["processes"] = {
                "total": len(procs),
                "top_cpu": procs[:10]
            }

        if alert_threshold:
            alerts = []
            if data.get("cpu", {}).get("average", 0) > 80:
                alerts.append("CRITICAL: CPU usage > 80%")
            if data.get("memory", {}).get("percent", 0) > 90:
                alerts.append("CRITICAL: Memory usage > 90%")
            if data.get("memory", {}).get("available_gb", 0) < 0.5:
                alerts.append("WARNING: Available memory < 512MB")
            if data.get("temperature"):
                for sensor, entries in data["temperature"].items():
                    if isinstance(entries, list):
                        for e in entries:
                            if isinstance(e, dict) and e.get("current", 0) > 80:
                                alerts.append(f"WARNING: {e.get('label', sensor)} temperature {e['current']}°C > 80°C")
            if not alerts:
                alerts.append("OK: All metrics within normal range")
            data["alerts"] = alerts

        json_str = json.dumps(data, indent=2, default=str)

        # Write results to workspace so commit_project can find them
        output_path = None
        if self.workspace:
            os.makedirs(self.workspace, exist_ok=True)
            # Include metric name in filename so multiple calls don't overwrite each other
            safe_metric = metric.replace(" ", "_")
            output_path = os.path.join(self.workspace, f"system_monitor_{safe_metric}.json")
            with open(output_path, "w") as f:
                f.write(json_str)

        result = json_str
        if output_path:
            result += f"\n\nResults saved to: {output_path}"
        return result


class SystemSummaryTool(BaseTool):
    name = "system_summary"
    description = (
        "Get a quick human-readable summary of system health. "
        "Use this before launching heavy parallel tasks to check if resources are available."
    )
    parameters = {
        "type": "object",
        "properties": {
            "minimal": {
                "type": "boolean",
                "description": "Return a one-line summary (default: false)"
            }
        },
        "required": []
    }
    category = "system"
    fallback_name = "system_monitor"

    async def execute(self, minimal: bool = False) -> str:
        try:
            import psutil
        except ImportError:
            return "Error: 'psutil' is required. Install with: pip install psutil"

        cpu = psutil.cpu_percent(interval=0.3)
        mem = psutil.virtual_memory()
        load = psutil.getloadavg() if hasattr(psutil, "getloadavg") else (0, 0, 0)

        if minimal:
            temp_str = ""
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    for entries in temps.values():
                        if entries:
                            temp_str = f" | Temp: {entries[0].current}°C"
                            break
            except Exception:
                pass
            return f"CPU: {cpu}% | RAM: {mem.percent}% ({mem.used//(1024**2)}MB/{mem.total//(1024**2)}MB){temp_str}"

        lines = [
            f"System Health Summary",
            f"{'='*40}",
            f"CPU Usage:       {cpu}% (Load: {load[0]:.1f}, {load[1]:.1f}, {load[2]:.1f})",
            f"Memory:          {mem.percent}% ({mem.used//(1024**2)}MB / {mem.total//(1024**2)}MB)",
            f"Available RAM:   {mem.available//(1024**2)}MB",
            f"Swap:            {psutil.swap_memory().percent}%",
        ]

        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for e in entries:
                        lines.append(f"Temperature ({name}): {e.current}°C")
                        break
                    break
        except Exception:
            pass

        lines.append(f"{'='*40}")
        if cpu > 80:
            lines.append("⚠️  High CPU usage - consider serializing tasks")
        if mem.percent > 90:
            lines.append("⚠️  Low memory - defer heavy operations")
        if mem.available < 512 * 1024 * 1024:
            lines.append("⚠️  Critical memory - immediate action recommended")
        if cpu < 50 and mem.percent < 70:
            lines.append("✅ System healthy - ready for parallel tasks")

        return "\n".join(lines)
