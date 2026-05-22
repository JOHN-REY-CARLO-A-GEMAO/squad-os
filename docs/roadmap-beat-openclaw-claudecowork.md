# SquadOS Capability Roadmap

> **Mission:** Build the definitive open-source desktop AI agent platform
> **Current State:** Core orchestration working, security hardened, browser automation functional
> **Next Focus:** Multi-agent concurrency, desktop UI understanding
> **Last Updated:** May 22, 2026

---

## Current System State

### ✅ Working Capabilities
- **Multi-model routing** via LiteLLM (Ollama cloud: `glm-4.7`)
- **Secure terminal execution** with command allowlist + path traversal protection
- **Windows compatibility layer** (Unix → PowerShell translation)
- **Browser automation** via Playwright (`BrowserControlTool`)
- **File system sandboxing** via `ProjectBranch`
- **Human-in-the-loop approvals** via dashboard (`DashboardApprovalTool`)
- **24/7 autonomous worker loop** (polling-based mission execution)
- **Tool-level retry handlers** with fallback chains
- **Role validation** in mission planning (prevents fake agent roles)
- **Duplicate filename handling** (directory-aware naming in commits)
- **DAG-based parallel execution** (wave-based task scheduling with dependency resolution)
- **Blackboard integration** (task result sharing between agents)
- **Circular dependency detection** (graceful handling of invalid dependency graphs)
- **Agent swarm coordination** (dynamic task reassignment, load balancing, performance metrics)
- **Priority-based scheduling** (tasks sorted by priority and dependency count)
- **Adaptive concurrency** (suggested_parallelism from LLM planning)
- **Desktop UI understanding** (accessibility tree extraction via `UIInspectorTool` on Windows/macOS/Linux)
- **Native integrations** (Telegram, Discord, Email via dedicated tools)

### 🔄 In Progress
- **Skill marketplace** (tool discovery and dynamic loading)

###  Planned
- Scheduling/cron workflows
- Self-healing agents
- Rich HITL (WebSocket notifications, structured forms)

---

## Lessons Learned

### Model Selection
- ✅ `ollama/glm-4.7` — Supports tool calling, reliable, free tier
-  `ollama/gemma3:*` — Doesn't generate proper `tool_calls`, returns JSON in content
- ❌ `ollama/deepseek-v3.2` — Requires paid subscription
- ️ Ollama cloud free tier — Rate limited, some models unavailable
- **Lesson:** Test tool calling support before committing to a model

### Security Filter Tuning
- **Problem:** Initial implementation blocked legitimate Windows flags (`dir /s /b`)
- **Root cause:** Path traversal check treated all tokens as potential paths
- **Solution:** `_looks_like_path()` distinguishes flags (`/s`, `-la`, `--verbose`) from actual paths
- **Balance:** Block `../` traversal, allow command flags
- **Lesson:** Security filters must understand command syntax, not just pattern match

### Cross-Platform Compatibility
- **Problem:** Agents generate Unix commands (`mkdir -p`, `touch`, `ls`)
- **Impact:** Commands fail on Windows with "syntax incorrect" errors
- **Solution:** `_translate_unix_to_windows()` in `TerminalTool`
  - `mkdir -p` → `New-Item -ItemType Directory -Force`
  - `touch` → `New-Item -ItemType File -Force`
  - `ls` → `Get-ChildItem -Force`
- **Lesson:** Abstract command execution or provide translation layer for cross-platform support

### Agent Behavior Patterns
- **Problem:** LLMs invent roles (`Researcher`, `Analyst`, `Writer`) not in hired squad
- **Impact:** Tasks skipped with "role not found" errors
- **Solution:** Strict role validation in `plan_mission()` with retry on invalid roles
- **Lesson:** Constrain LLM output with explicit allowed values, validate post-parse

### File Handling
- **Problem:** Multiple `__init__.py` files created 176 numbered duplicates (`___init___1.py`, etc.)
- **Root cause:** Commit tool used numeric suffixes without directory context
- **Solution:** Directory-aware naming (`module1___init__.py` vs `module2___init__.py`)
- **Lesson:** Preserve structural information when handling duplicate filenames

### Repository Management
- **Problem:** 101 stale branches from closed PRs, runtime files tracked in git
- **Impact:** Cluttered repository view, accidental exposure of `.env`, `workspace/`, `*.db`
- **Solution:** Aggressive `.gitignore` + `git rm --cached` cleanup
- **Result:** 41 clean source files tracked, 8 active branches
- **Lesson:** Regular repository hygiene prevents technical debt accumulation

---

## Competitive Landscape

| Dimension | SquadOS | OpenClaw | Claude Cowork |
|-----------|---------|----------|---------------|
| **Desktop Understanding** | ✅ Accessibility tree extraction | ❌ Raw coordinates | ❌ Raw coordinates |
| **Security** | ✅ Command allowlist + path traversal |  All-or-nothing | ❌ Trusts model blindly |
| **Open Source** | ✅ Full transparency | ✅ | ❌ Proprietary |
| **Cost** | ✅ Free self-hosted | ~$20/mo + API | $17-200/mo |
| **Multi-Agent** | ✅ DAG parallel + swarm coordination | ✅ Parallel | ❌ Single agent |
| **Browser Automation** | ✅ Playwright | ❌ | ❌ |
| **Human-in-the-Loop** | ✅ Dashboard approvals | ⚠️ Limited | ✅ Basic |
| **Native Integrations** | ✅ Telegram, Discord, Email | ✅ 25+ channels | ❌ Desktop only |
| **Skill Marketplace** |  None | ✅ ClawMart | ❌ None |
| **Scheduling** | ❌ None | ✅ Cron | ✅ Basic |

**Key Differentiators:**
1. **Security-first design** — Command validation, path traversal protection, audit logging
2. **Cross-platform compatibility** — Windows/Linux support with command translation
3. **Open source transparency** — Full code access, self-hosted, no vendor lock-in
4. **Browser automation** — Playwright-based web interaction (unique capability)

---

## Implementation Priority

### Phase 1 — Foundation ✅ COMPLETED
1. ✅ Security hardening (command validation, path traversal protection)
2. ✅ Windows compatibility layer (Unix → PowerShell translation)
3. ✅ Browser automation (Playwright-based `BrowserControlTool`)
4. ✅ Human-in-the-loop approvals (`DashboardApprovalTool`)
5. ✅ File system sandboxing (`ProjectBranch`)
6. ✅ Tool-level retry handlers with fallback chains
7. ✅ Role validation in mission planning
8. ✅ Duplicate filename handling (directory-aware naming)
9. ✅ Repository cleanup (41 clean files, proper `.gitignore`)

### Phase 2 — Concurrency 🔄 IN PROGRESS
1. 🔄 DAG task planner (replace sequential execution)
2. 🔄 Async task graph executor (`asyncio.gather()`)
3. 🔄 Blackboard-as-results-store (replace context string)
4. 🔄 Dependent task scheduling

**Why now:** OpenClaw's parallelism is its main technical advantage. Closing this gap enables complex mission workflows and reduces execution time.

### Phase 3 — Desktop Intelligence 📋 PLANNED
1.  `inspect_element` tool — Windows UI Automation tree extraction
2. 📋 `click_element` — coordinate-free UI interaction (accessibility ID)
3. 📋 `wait_for_element` — block until UI element appears
4. 📋 CV-based element detector (fallback for non-accessible apps)

**Why next:** Directly competes with Claude Cowork's "Computer Use" feature. Semantic UI understanding > raw coordinates.

### Phase 4 — Integrations 📋 PLANNED
1.  Telegram bot integration (`python-telegram-bot`)
2. 📋 Discord bot integration (`discord.py`)
3. 📋 Email (SMTP/IMAP) tools
4. 📋 Watch folder trigger (`watchdog`)
5. 📋 Webhook receiver (HTTP endpoint)

**Why fourth:** OpenClaw's ecosystem breadth is its moat. Starting with Telegram/Discord chips away at that advantage.

### Phase 5 — Ecosystem 📋 PLANNED
1.  Skill marketplace (`skills/` directory convention)
2. 📋 Skill YAML schema
3. 📋 Pre-built skills (researcher, data-analyst, document-writer)
4. 📋 In-dashboard skill browser

**Why fifth:** Creates a flywheel — users contribute skills, which attracts more users, which creates more skills.

### Phase 6 — Advanced Workflows 📋 PLANNED
1. 📋 Scheduling system (`schedules` table + cron checker)
2.  `schedule_mission` tool
3.  Self-healing agents (error classification + auto-retry)
4. 📋 Rich HITL (WebSocket notifications, structured forms)

**Why sixth:** Closes the "always-on" capability gap with OpenClaw.

---

## Quick Wins (Next 2 Weeks)

1. **Accessibility tree extraction** — `pywinauto` or `comtypes` for Windows UI Automation
2. **DAG task planner** — Enable parallel agent execution
3. **WebSocket HITL** — Real-time approval notifications (replace polling)
4. **Telegram integration** — First native channel
5. **Skill marketplace foundation** — `skills/` directory convention

---

## Architecture Overview

```
User Input (Dashboard/Chat)
    ↓
Manager (Orchestrator)
    ├── Recruit Squad (role validation)
    ├── Plan Mission (DAG planner → parallel tasks)
    └── Execute Tasks (async task graph)
            ↓
        BaseAgent
            ├── Tool Execution (with retry/fallback)
            ├── ProjectBranch (file sandboxing)
            └── Blackboard (shared state)
            ↓
        Tools Registry
            ├── TerminalTool (security validated + Windows translation)
            ├── BrowserControlTool (Playwright)
            ├── FileWriterTool / ReadFileTool
            ├── WebSearchTool (DuckDuckGo)
            └── DashboardApprovalTool (HITL)
            ↓
        SQLite Persistence
            ├── Missions / Tasks
            ├── Blackboard
            ├── Schedules (future)
            └── Memory Graph (future)
```

### Key Components

| Component | File | Status |
|-----------|------|--------|
| **Manager** | `squad_os/orchestrator/manager.py` | ✅ Working (sequential), 🔄 DAG in progress |
| **BaseAgent** | `squad_os/agents/base.py` | ✅ Working with retry/fallback |
| **TerminalTool** | `squad_os/tools/registry.py` | ✅ Security hardened + Windows translation |
| **BrowserControlTool** | `squad_os/tools/visual.py` | ✅ Playwright-based |
| **ProjectBranch** | `squad_os/core/projects.py` | ✅ File sandboxing + directory-aware commits |
| **Dashboard** | `dashboard.py` | ✅ Streamlit UI with HITL |
| **Worker** | `worker.py` | ✅ 24/7 mission polling loop |

---

## Technical Debt & Known Issues

### High Priority
- **Sequential task execution** — Limits mission complexity and speed
- **Polling-based HITL** — Dashboard approval requires page refresh
- **No native integrations** — Limited to dashboard chat interface

### Medium Priority
- **Model dependency** — Tied to Ollama cloud, needs fallback options
- **No error classification** — All tool failures treated equally
- **Limited memory** — `memory_search` only searches task outputs, no semantic search

### Low Priority
- **Duplicate branch cleanup** — 8 stale branches remain (acceptable)
- **Documentation gaps** — API docs, setup guides need improvement
- **Test coverage** — 4 test files, needs comprehensive suite

---

## Success Metrics

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| **Task Execution Time** | Sequential (slow) | Parallel (3-5x faster) | Q2 2026 |
| **Supported Platforms** | Windows only | Windows + Linux + macOS | Q3 2026 |
| **Native Integrations** | 0 | 4 (Telegram, Discord, Email, Webhook) | Q3 2026 |
| **Skills Available** | 0 | 5+ pre-built skills | Q4 2026 |
| **Test Coverage** | ~20% | 80%+ | Q4 2026 |
| **GitHub Stars** | 0 | 100+ | Q4 2026 |

---

*Sources:*
- *[OpenClaw vs Claude Code vs ClaudeClaw (DEV Community, March 2026)](https://dev.to/talien8575/openclaw-vs-claude-code-vs-claudeclaw-which-ai-agent-setup-should-you-use-in-2026-4b6f)*
- *[Building ClaudeClaw: An OpenClaw-Style Autonomous Agent System (Medium, March 2026)](https://medium.com/@mcraddock/building-claudeclaw-an-openclaw-style-autonomous-agent-system-on-claude-code-fe0d7814ac2e)*
- *[Claude Cowork — Anthropic Product](https://www.anthropic.com/product/claude-cowork)*
- *[Cowork: Claude Code power for knowledge work](https://claude.com/cowork)*
- *[Get started with Cowork — Claude Help Center](https://support.claude.com/en/articles/13345190-getting-started-with-cowork)*

---

*Document Status: Living document — updated with each major milestone*
*Next Review: June 2026 (after DAG planner implementation)*
