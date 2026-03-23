# SquadOS Framework

SquadOS is a production-ready Multi-Agent System (MAS) framework built for Python, designed with an "Orchestrator-Managed Pipeline" architecture. It emphasizes modularity, security, and observability.

## Key Features

- **Asynchronous Execution:** Built with `asyncio` for non-blocking I/O operations.
- **SQLite State Management:** Uses SQLite with Write-Ahead Logging (WAL) for ACID-compliant task tracking and auditing.
- **Sandboxed File Operations:** Tools like `FileWriterTool` are restricted to a designated `workspace/` directory.
- **LiteLLM Integration:** Compatible with any major LLM provider (OpenAI, Anthropic, Gemini, etc.) via a unified API.
- **Structured Planning:** The `Manager` uses Pydantic models and LLM structured outputs to generate consistent mission plans.
- **Observability:** Automatically tracks prompt/completion tokens, costs (USD), and execution latency for every task.
- **Resilient Workflows:** Built-in cyclical retry loop (max 3 retries) for tasks that fail QA validation.

## Architecture

1. **Manager (Orchestrator):** The brain of the squad. It takes a high-level goal, uses a "Planner" LLM to break it into a task list, and assigns them to agents. It manages the "Direct Handoff" of context between agents.
2. **BaseAgent:** A persona-driven class with a specific role, goal, and backstory. Each agent has its own toolset and reasoning loop.
3. **Tools (Registry):** Modular components that agents can use to interact with the world (e.g., `WebScraperTool`, `FileWriterTool`).
4. **Database (Shared Memory):** A centralized SQLite database (`shared_memory.db`) that stores the complete history and state of all missions and tasks.

## Quick Start

### Installation

Ensure you have Python 3.10+ installed.

```bash
# Clone the repository and navigate into it
cd squad_os

# Install dependencies (using uv or pip)
pip install .
```

### Configuration

Create a `.env` file in the root directory:

```env
# Cloud AI
OPENAI_API_KEY=your_api_key_here

# Local AI Mode (Ollama)
LOCAL_AI_MODE=false
OLLAMA_API_BASE=http://localhost:11434
```

### Run the Demo

The demo showcases a "Researcher" finding information and a "Developer" building a Flask app based on that research, followed by a "QA/Reviewer" validation.

```bash
python main.py
```

## Adding New "Departments"

To add a new specialized team (department), follow these steps:

1. **Define Tools:** Create new tool classes in `squad_os/tools/registry.py` by inheriting from `BaseTool`.
2. **Instantiate Agents:** Create new `BaseAgent` instances with specific roles and tools.
3. **Update Manager:** Pass the new agents to the `Manager` class.

Example:

```python
from squad_os.agents.base import BaseAgent
from squad_os.tools.registry import SearchTool

social_media_manager = BaseAgent(
    role="Social Media Specialist",
    goal="Create engaging posts for LinkedIn and Twitter based on technical articles.",
    backstory="A creative content creator with a deep understanding of tech trends.",
    tools=[SearchTool()]
)

# Add it to the manager's agent list
manager = Manager(agents=[researcher, developer, qa, social_media_manager])
```

## Development and Testing

The framework is designed to be extensible. To add new features, follow the patterns in the `squad_os/` subdirectories. Ensure all new logic is `async` compatible.
