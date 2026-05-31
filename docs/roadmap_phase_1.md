# 🛡️ Phase 1: Hardware & Foundation (Month 1)

## 📡 MCP Connectivity Strategy
**Objective:** Standardize tool execution by enabling SquadOS to act as an MCP Client.

### Architecture: `MCPClientManager`
- **Library:** `mcp-python-sdk`
- **Implementation:**
    - Create `squad_os/tools/mcp_hub.py` to handle lifecycle of MCP server connections (stdio/SSE).
    - **Dynamic Discovery:** On startup, the `SkillRegistry` scans a `mcp_servers.json` config to initialize connections.
    - **Wrapper Tool:** A generic `MCPWrapperTool` that translates SquadOS `execute()` calls into MCP `call_tool` requests.
- **Benefits:** Access to the growing ecosystem of MCP-ready tools (e.g., Brave Search, GitHub, Postgres) without writing native SquadOS wrappers.

---

## 🖥️ The "Dedicated Mini Screen" (Axiom View)
**Objective:** Provide a low-overhead, real-time status display optimized for small RPi screens (e.g., 3.5" - 7" TFTs).

### Design: `mini_dashboard.py`
- **Tech:** Streamlit (standard) with a `query_param` toggle or a dedicated lightweight FastAPI + Tailwind sub-page.
- **Key Views:**
    - **Pulse:** Heartbeat of the active mission (current task, assigned agent).
    - **Visuals:** Last captured screenshot from `BrowserControlTool` or `VisionAnalysisTool`.
    - **Logs:** 3-line rolling log of the most recent tool executions.
- **Hardware Integration:** Auto-launch in kiosk mode on the local X11/Wayland session of the RPi 5.

---

## 🌡️ RPi 5 Resource Monitor Tool
**Objective:** Real-time health tracking and resource-aware task scheduling.

### Implementation: `SystemMonitorTool`
- **Library:** `psutil` and `gpiozero` (for RPi-specific temp sensors).
- **Metrics:**
    - CPU Load (per core).
    - Memory usage (with OOM alerts).
    - CPU Temperature (Throttle detection).
    - Disk I/O (Workspace health).
- **Orchestrator Integration:** The `Manager` will check `SystemMonitorTool` results before launching "Heavy" parallel waves. If Temp > 80°C or RAM < 10%, it will serialize tasks to prevent crashes.

---

## 🛠️ Validation Criteria (RPi 5)
1. **Idle Overhead:** SquadOS Worker + Dashboard must consume < 512MB RAM when idle.
2. **Thermal Load:** Running a 3-agent swarm must not exceed 85°C with standard active cooling.
3. **MCP Latency:** Local stdio MCP tool calls must resolve in < 200ms (excluding LLM processing).
