# Architecture Overview — Squad OS

This document outlines the high-level architecture of Squad OS and sets the foundation for our multi-agent, multi-platform ecosystem.

---

## 1. High-Level System Architecture

Squad OS is built on a modular, asynchronous architecture designed to handle complex multi-agent execution safely, efficiently, and resiliently. The ecosystem spans across background workers, a desktop orchestrator dashboard, and a mobile remote controller interface.

```
                  +--------------------------------------------+
                  |             SQUAD OS ECOSYSTEM             |
                  +--------------------------------------------+
                                /                      \
                               /                        \
                  +--------------------+        +--------------------+
                  |  Desktop Dashboard |        | Mobile Companion   |
                  |  (Streamlit App)   |        | (Flutter App)      |
                  +--------------------+        +--------------------+
                            ^                             |
                            |                             |
                            v                             v
                  +--------------------------------------------+
                  |           Squad OS Backend API             |
                  |     (FastAPI, WebSocket, SQLite DB)        |
                  +--------------------------------------------+
```

---

## 2. Core Architectural Principles

1. **Agent Autonomy & Orchestration:** High-level user targets are broken down into a Directed Acyclic Graph (DAG) of discrete tasks. A centralized orchestrator (Manager) delegates these tasks to specialized base agent personas.
2. **Unified Event Sourcing:** Rather than raw state queries, the timeline and state of the system are driven by an immutable event log. Any device can deterministically reconstruct system status by replaying these sequenced events.
3. **Local-First & Sync Resiliency:** Applications in the ecosystem are designed to run offline or in low-network coverage environments. Local caches are synchronized periodically, resolving potential conflicts using standard, robust policy matrices.
4. **Sandboxed Command Execution:** Any system action, shell command execution, or file write is tightly bound to isolated mission worktrees to safeguard host OS environments.

---

## 3. Core Ecosystem Components

* **Squad OS Backend API:** The core Python/FastAPI service managing local file systems, databases (`shared_memory.db`), orchestrators, and WebSockets.
* **Streamlit Desktop Dashboard:** The local control center for managing active squads, visualizing DAG progression, modifying agent personas, and browsing the Agent Store.
* **Mobile Companion App:** An elegant, conversation-first remote interface optimized for one-handed operation, human-in-the-loop approvals, and quick workspace commands.

---

## 4. Mobile Architecture Blueprint

The comprehensive, production-grade architecture of our mobile companion—including full database schema specifications, event-sourcing guidelines, communication handshake payloads, security matrices, and mockups—is located inside the dedicated Mobile Companion blueprint:

👉 **[docs/MOBILE_REMOTE_COMPANION_PLAN.md](docs/MOBILE_REMOTE_COMPANION_PLAN.md)**
