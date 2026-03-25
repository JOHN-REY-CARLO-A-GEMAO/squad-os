# 🤖 SquadOS AI Context

This document provides a technical overview of the SquadOS framework, designed to help an AI agent or a developer quickly onboard to the codebase.

## 🏗️ Architecture Overview: Orchestrator-Managed Pipeline

SquadOS follows an **Orchestrator-Managed Pipeline** architecture. The core logic resides in a centralized `Manager` that coordinates a "squad" of specialized `BaseAgent` instances.

### 🧠 Manager (Orchestrator)
- **File:** `squad_os/orchestrator/manager.py`
- **Role:** Breaks down a high-level mission goal into a series of sequential tasks.
- **Key Logic:**
    - `plan_mission(goal)`: Uses an LLM to generate a JSON `MissionPlan` containing a list of `TaskPlan` objects.
    - `run_mission(goal)`: Iterates through tasks, assigns them to agents (using fuzzy matching for role names), and manages execution.
    - **QA Loop:** If a task is assigned to a "QA/Reviewer" role and the output contains failure keywords (e.g., "fail", "bug"), the manager triggers a retry mechanism (up to `max_retries`).

### 🕵️ BaseAgent
- **File:** `squad_os/agents/base.py`
- **Role:** Persona-driven agent that executes individual tasks using assigned tools.
- **Key Logic:**
    - `execute_task(task_description, context)`: A reasoning loop that handles tool-calling via `litellm`.
    - **Multi-turn Reasoning:** Currently supports a 1-turn tool-calling loop (can be expanded).
    - **LiteLLM Integration:** Agnostic to the model provider (OpenAI, Anthropic, Ollama, etc.).

---

## 💾 Shared Memory & Persistence

SquadOS uses SQLite for mission auditing and state management.

- **File:** `squad_os/database/session.py`
- **Database Path:** `shared_memory.db` (WAL mode enabled for concurrent access).

### 📊 Schema Details

#### `missions` Table
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | INTEGER | Primary Key (Autoincrement) |
| `goal` | TEXT | The high-level mission objective |
| `status` | TEXT | `PENDING`, `IN_PROGRESS`, `COMPLETED`, `FAILED` |
| `created_at` | TIMESTAMP | Creation time |

#### `tasks` Table
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | INTEGER | Primary Key (Autoincrement) |
| `mission_id` | INTEGER | Foreign Key to `missions.id` |
| `description` | TEXT | The specific instruction for the task |
| `assigned_agent` | TEXT | The role name of the assigned agent |
| `status` | TEXT | `PENDING`, `COMPLETED`, `FAILED`, `FAILED_QA` |
| `input_data` | TEXT | (Optional) Input context |
| `output_data` | TEXT | The final result from the agent |
| `error` | TEXT | Error message if the task failed |
| `prompt_tokens` | INTEGER | LiteLLM usage metric |
| `completion_tokens` | INTEGER | LiteLLM usage metric |
| `cost_usd` | REAL | Estimated cost of the task |
| `execution_ms` | INTEGER | Execution time in milliseconds |
| `retry_count` | INTEGER | Number of retries attempted |

---

## 🛠️ Tooling & Sandboxing

All tools are registered in `squad_os/tools/registry.py` and inherit from `BaseTool` (`squad_os/tools/base.py`).

### 🛡️ Security & Sandboxing
- **`FileWriterTool`**: Sandboxed to the `workspace/` directory. Attempts to write outside this directory will return a security violation error.
- **`TerminalTool`**: Executes shell commands. *Use with caution.*

### 🔍 Available Tools
- `web_scrape`: Scrapes a URL and returns Markdown (max 8000 chars).
- `write_file`: Writes content to the `workspace/` sandbox.
- `web_search`: Real-time search via DuckDuckGo.
- `terminal`: Executes shell commands.
- `human_approval`: Pauses execution to wait for user input (HITL).

---

## 🚀 Development Guidelines

### ➕ How to add a new Tool
1. Create a new class in `squad_os/tools/registry.py` (or a new file in `squad_os/tools/`).
2. Inherit from `BaseTool`.
3. Implement `name`, `description`, `parameters` (JSON Schema), and the `async execute` method.
4. If it's a new file, import and register it where needed (e.g., in `main.py`).

### 🏷️ Naming Conventions
- **Agent Roles:** Use descriptive, capitalized names (e.g., "Senior Developer", "Security Auditor").
- **Memory Keys:** When passing context between agents, the `Manager` automatically appends the previous agent's output. For custom keys, use `snake_case`.

### 🧪 Adding New Agent Personas
- Define a new `BaseAgent` instance in `main.py` with a specific `role`, `goal`, and `backstory`.
- Ensure the `Manager` is initialized with the new agent.

---

## 🔧 Environment Setup
- **Python Version:** `>=3.10`
- **Installation:** `pip install -r requirements.txt`
- **Environment Variables:**
  - `OPENAI_API_KEY`: For cloud models.
  - `LOCAL_AI_MODE`: Set to `true` to use Ollama.
  - `TAVILY_API_KEY`: (Optional) If using Tavily for search (the default is DuckDuckGo).

## 📊 Observability
- **Dashboard:** A Streamlit-based UI is available for real-time monitoring.
- **Command:** `cd workspace && python -m streamlit run dashboard.py` (Note: Ensure `dashboard.py` exists in your workspace or adjust path).
