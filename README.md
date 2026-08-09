# 🛡️ SquadOS Framework

<div align="center">
  <video src="https://github.com/JOHN-REY-CARLO-A-GEMAO/squad-os/raw/main/assets/promo.mp4" width="800" autoplay loop muted playsinline>
    Your browser does not support the video tag.
  </video>
</div>

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Ollama](https://img.shields.io/badge/Ollama-ready-green)](https://ollama.com/)

**SquadOS** is a production-ready, asynchronous Multi-Agent System (MAS) framework. It orchestrates specialized AI agents—Architects, Developers, Researchers, QA reviewers—to autonomously break down goals, execute tasks in parallel via DAG-based workflows, and produce tangible outputs.

Includes an **Agent Store** ecosystem for packaging, sharing, and deploying reusable multi-agent workflows as `.sqad` bundles.

---

## 🚀 Key Features

- **Asynchronous Orchestration:** DAG-based task execution with parallel waves, swarm consensus, and dynamic reassignment.
- **Agent Store Ecosystem:** Package, install, and run reusable multi-agent workflows as `.sqad` bundles. Built-in CLI to compile from `squad.yaml`.
- **Pre-built Workflows:** Store workflows execute with exact role/tool definitions — zero LLM re-planning overhead.
- **SQLite Persistence:** Full mission auditing and state management in `shared_memory.db` with WAL mode.
- **Human-in-the-Loop (HITL):** Built-in safety protocols with polling and WebSocket-based approval.
- **Provider Agnostic:** Powered by LiteLLM. Seamlessly switch between OpenAI, Anthropic, or local **Ollama** models.
- **Agentic Dashboard:** Real-time Streamlit UI for mission control, agent personas, project browsing, and the Agent Store.
- **Scheduling Engine:** Cron-like mission scheduling with persistent schedule history.
- **Self-Healing:** Error classification, retry with exponential backoff, health monitoring, and fallback chains.
- **30+ Tools:** Web search, browser automation, desktop control, file I/O, terminal (sandboxed), email, Discord, Telegram, video processing, UI inspection, and more.
- **Security-First:** All commands validated against an allowlist, path traversal blocked, dangerous patterns rejected.

---

## 🛠️ Quick Start

### 1. Installation

```bash
git clone https://github.com/JOHN-REY-CARLO-A-GEMAO/squad-os.git
cd squad-os
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the root directory:

```env
# OpenAI (or any LiteLLM provider)
OPENAI_API_KEY=your_key_here

# Or use Ollama locally (no API key needed)
# SquadOS defaults to ollama/glm-4.7
```

### 3. Run the Worker

```bash
python worker.py
```

### 4. Run the Dashboard

In a separate terminal:

```bash
streamlit run dashboard.py
```

---

## 💾 Agent Store

SquadOS includes a full package management system for multi-agent workflows.

### Package Format (`.sqad`)

A `.sqad` file is a zip bundle containing:

```
my-workflow.sqad
├── manifest.json          # Metadata (id, name, version, author, tags)
├── workflow.json          # DAG task definitions
├── tools/                 # Custom Python tool modules
├── agents/                # Custom agent persona definitions
├── assets/                # Static resources
└── requirements.txt       # Pip dependencies
```

### Authoring with `squad.yaml`

Write a single YAML file and compile it:

```yaml
# squad.yaml
id: social-monitor
name: Social Media Monitor
version: 1.0.0
author:
  handle: "@dev_guru"
  url: https://github.com/dev_guru
description: Scans social channels and summarizes trends.
tags: [social, monitoring]
assumes_tools: [web_search, send_discord]

agents:
  - role: Social Scraper
    goal: Find relevant mentions
    tools: [web_search]

  - role: Reporter
    goal: Format and post summary
    tools: [send_discord]

workflow:
  name: Weekly Scan
  tasks:
    - description: Search for mentions MUST use web_search tool
      assigned_agent_role: Social Scraper
      depends_on: []
    - description: Post summary to channel MUST use send_discord tool
      assigned_agent_role: Reporter
      depends_on: [0]
```

Build it:

```bash
python -m squad_os.store.cli build ./squad.yaml
# Produces ./social-monitor.sqad
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `python -m squad_os.store.cli build <squad.yaml>` | Compile a squad.yaml into a .sqad package |
| `python -m squad_os.store.cli build <squad.yaml> -o <path>` | Build with custom output path |

### Store Tools (available to agents)

| Tool | Description |
|------|-------------|
| `browse_store` | List available packages, filter by search/tag |
| `install_package` | Install a .sqad from file path or store catalog |
| `run_workflow` | Execute a stored workflow as a mission |
| `uninstall_package` | Remove an installed package |

### Dashboard

The **💾 Agent Store** tab provides:

- **Browse** — search and install packages from the catalog
- **Installed** — view installed packages, inspect workflows, deploy as missions
- **Upload .sqad** — sideload packages with validation feedback

---

## 💡 Real-World Examples

Explore the `examples/` directory:

- **Java GUI Builder:** A squad of agents (Architect, Developer, QA) collaborating to build a Java Swing Login system with validation and error handling.
- **Framework Researcher:** Agents performing live web searches to summarize the competitive landscape of AI tools.

Build your own workflow package and share it with the community.

---

## 🏗️ Architecture

```
User Input (Dashboard / API / Queue)
        |
    Manager (Orchestrator)
        |-- Recruit Squad (dynamic hiring via LLM or pre-built workflow)
        |-- Plan Mission (LLM-generated DAG or loaded from store)
        |-- Execute DAG (wave-based parallel execution)
                |
            BaseAgent (persona-driven, multi-turn reasoning loop)
                |-- Tool calling via LiteLLM
                |-- Retry / fallback on failure
                        |
                    Tools Registry (30+ tools)
                    AgentPackageLoader (.sqad lifecycle)
                    SkillRegistry (dynamic tool discovery)
                        |
                    SQLite Persistence (shared_memory.db)
```

### Key Components

| Component | Description |
|-----------|-------------|
| **Manager** | The orchestrator. Recruits agents, plans DAGs, executes waves, handles failures and reassignment. |
| **BaseAgent** | Persona-driven agent with role, goal, backstory. Multi-turn tool-calling loop. |
| **AgentPackageLoader** | Loads, validates, installs, and removes .sqad packages. Discovers custom tools from packages. |
| **ProjectBranch** | Sandboxed file workspace per mission. Handles forking, logging, committing, archiving. |
| **SkillRegistry** | Auto-discovers tools from `squad_os.tools` and installed packages. |
| **ScheduleManager** | Cron-like scheduling for recurring missions. |

---

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | API key for OpenAI (or other LiteLLM provider) |
| `SQUAD_OS_MODEL` | `ollama/glm-4.7` | Default LLM model for agents |
| `SQUAD_OS_LLM_CONCURRENCY` | `5` | Max concurrent LLM calls |

### Database

SquadOS uses SQLite with automatic migration support. The database (`shared_memory.db`) includes tables for missions, tasks, approvals, blackboard, schedules, agent personas, and store packages.

---

## 📜 License

Distributed under the **Apache 2.0 License**. See `LICENSE` for more information.

Built with ❤️ by **JOHN-REY-CARLO-A-GEMAO**
