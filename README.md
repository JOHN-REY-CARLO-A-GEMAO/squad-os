# 🛡️ SquadOS Framework

[](https://opensource.org/licenses/Apache-2.0)
[](https://www.python.org/)
[](https://ollama.com/)

**SquadOS** is a production-ready, asynchronous Multi-Agent System (MAS) framework. It utilizes an **Orchestrator-Managed Pipeline** to coordinate specialized agents—such as Architects, Developers, and Researchers—for complex automation tasks.

-----

## 🚀 Key Features

  * **Asynchronous Orchestration:** High-speed agent coordination using `asyncio` for non-blocking I/O.
  * **SQLite Persistence:** Full mission auditing and state management in `shared_memory.db` with WAL mode.
  * **Human-in-the-Loop (HITL):** Built-in safety protocols where agents request human approval via the terminal before executing critical actions.
  * **Provider Agnostic:** Powered by LiteLLM. Seamlessly switch between OpenAI, Anthropic, or local **Ollama** models.
  * **Agentic Dashboard:** Real-time observability to monitor token costs, latency, and agent logs via a built-in Streamlit UI.

-----

## 🛠️ Quick Start

### 1\. Installation

```bash
git clone https://github.com/JOHN-REY-CARLO-A-GEMAO/squad-os.git
cd squad-os
pip install -r requirements.txt
```

### 2\. Configuration

Create a `.env` file in the root directory:

```env
OPENAI_API_KEY=your_key_here
# SquadOS also supports Ollama out of the box!
```

### 3\. Run the Monitoring Dashboard

```bash
cd workspace
python -m streamlit run dashboard.py
```

-----

## 💡 Real-World Examples

Explore the `examples/` directory to see SquadOS in action:

  * **Java GUI Builder:** A squad of agents (Architect, Developer, QA) collaborating to build a Java Swing Login system with validation and error handling.
  * **Framework Researcher:** Agents performing live web searches to summarize the competitive landscape of AI tools.

-----

## 🏗️ Architecture

  * **Manager (Orchestrator):** The "brain" that breaks high-level goals into task lists and manages agent handoffs.
  * **BaseAgent:** Persona-driven agents with specific roles, goals, and private toolsets.
  * **Tools Registry:** Modular components (WebSearch, FileWrite, Terminal) for real-world interaction.
  * **Shared Memory:** A central SQLite DB for persistent history of all missions and tasks.

-----

## 📜 License

Distributed under the **Apache 2.0 License**. See `LICENSE` for more information.

Built with ❤️ by **JOHN-REY-CARLO-A-GEMAO**

-----