# ROADMAP.md — Squad OS

_Current as of 2026-05-18 | Axiom 🧠_

---

## Overview

Squad OS is an **agentic operating framework** designed to manage a squad of specialized AI workers, orchestrated by a lead intelligence (Axiom). This roadmap defines the four-phase development plan, culminating in a governance-first production platform.

---

## Phase 1 — Foundations ✅

**Goal:** Establish the core infrastructure and prove the system works.

### Objectives
- [x] Initialize repository with TypeScript/Node.js
- [x] Set up directory structure (`src/core`, `src/agents`, `src/tools`, `data/logs`)
- [x] Create identity and operating manifesto
- [x] Establish memory and logging conventions
- [x] Build `pulse.ts` — the heartbeat script
- [x] Define core orchestration primitives in `src/core`

### Deliverables
- `package.json` with TypeScript, tsx, @types/node
- `tsconfig.json` (strict mode, ES2022)
- `docs/squad/MANIFESTO.md`
- `src/core/pulse.ts` — Squad OS heartbeat
- `data/logs/` — persistent execution log directory

---

## Phase 2 — Agentic Swarm ✅

**Goal:** Move from single-threaded execution to a multi-agent dispatch system.

### Objectives
- [x] Build a **Dispatcher** agent in `src/core/Dispatcher.ts`
  - Understands high-level goals and breaks them into sub-tasks
  - Maintains a task queue with status tracking
- [x] Create specialized **Worker** agents:
  - `src/agents/BaseAgent.ts` — abstract base with id, role, status, processTask
  - `src/agents/ResearcherAgent.ts` — research-focused worker
- [x] Implement **agent communication protocol** (message-passing between agents)
- [x] Build a **task manifest** (`data/logs/squad.log`) — live tracking of all sub-tasks
- [x] Add `dispatchTask()` method with idle-agent matching

### Deliverables
- `src/agents/BaseAgent.ts` — abstract agent class
- `src/agents/ResearcherAgent.ts` — first specialized worker
- `src/core/Dispatcher.ts` — task orchestrator with registry
- `src/tools/Logger.ts` — timestamped, level-tagged append-only logger
- `data/logs/squad.log` — persistent execution log

---

## Phase 3 — Autonomy ✅

**Goal:** Squad OS runs continuously as a service, self-sustaining with an event loop.

### Objectives
- [x] **I/O directories** — `data/inbox/` (task ingestion) and `data/archive/` (processed tasks)
- [x] **Daemon event loop** — `src/core/Daemon.ts` watches inbox every 5s, dispatches tasks, archives results
- [x] **Inbox-based task dispatch** — drop a `.json` file `{ role, task }` → daemon handles the rest
- [x] **Autonomy integration test** — `src/test-autonomy.ts` validates the full loop end-to-end
- [x] Updated `src/main.ts` to start daemon in Listening Mode
- [ ] Background process persistence (systemd/supervisord — future)
- [ ] **GitHub API integration** — create Issues/PRs from tasks
- [ ] **Discord webhook notifier** — push status reports to a channel
- [ ] **Filesystem watcher** — react to file changes in real-time
- [ ] **Self-correction loop** — agents retry on failure automatically
- [ ] **Agent state persistence** — SQLite or JSON store for agent memory

### Deliverables
- `src/core/Daemon.ts` — 5-second event loop, inbox watcher, archive mover
- `src/main.ts` — daemon startup in Listening Mode
- `src/test-autonomy.ts` — integration test (spawns daemon, drops task, verifies archive)
- `data/inbox/` — task ingestion directory
- `data/archive/` — processed task storage
- `npm run test:autonomy` — validated end-to-end ✅

---

## Phase 4 — Production Readiness ✅

**Goal:** Transition from prototype to a governance-first platform with defense-in-depth across security, economics, scalability, observability, quality, resilience, and human oversight.

### Pillar 1: Security (Sandboxing & Guardrails)
- [x] **Docker Sandboxing** — `squad_os/core/sandbox.py` — `DockerExecutor` with `--cap-drop ALL`, `--network none`, resource limits (512MB RAM, 1 CPU, 64 PIDs), ephemeral containers
- [x] **TerminalTool (T3)** — runs in Alpine 3.19 sandbox
- [x] **PythonRunnerTool (T3)** — runs in Python 3.11-slim sandbox
- [x] **Input Guardrails** — `squad_os/core/guardrails.py` — 33 pattern-based rules across 8 categories (prompt injection, jailbreak, PII, toxicity, command injection, etc.)
- [x] **Tiered Risk Taxonomy** — `squad_os/core/tool_risk.py` — T0–T4 classification with HITL gates for T3/T4

### Pillar 2: Economics (Budget Guardrails)
- [x] **Mission Budget Caps** — `max_tokens`, `max_turns`, `max_cost_usd` per mission
- [x] **Real-time Tracking** — cumulative token counting across all turns
- [x] **Budget Exhaustion Interrupt** — pauses mission, moves to HITL queue
- [x] **Top Up & Resume** — human can increase limits during pause without losing context
- [x] **DB Migrations** — `missions` table extended with budget columns

### Pillar 3: Scalability (Context Engineering)
- [x] **ContextManager** — `squad_os/core/context.py` — sliding window (default 5 turns), max messages ceiling (default 20)
- [x] **Automatic Summarization** — pruned turns compressed into text summary
- [x] **Context Pinning** — system messages always preserved
- [x] **Resume Support** — context summary restored from snapshot on interrupt resume
- [x] **Token Reduction** — 40–60% input token savings on long missions

### Pillar 4: Observability (Structured Logging)
- [x] **SquadLogger** — `squad_os/core/logging.py` — correlation IDs (run_id, mission_id, task_id, agent_role)
- [x] **JSON Formatter** — machine-readable output for log aggregation (ELK, Datadog)
- [x] **Text Formatter** — human-readable with `[run] M#mission T#task [role]` prefix
- [x] **Timer Context Manager** — operation timing with structured output
- [x] **Full Migration** — all `print()` calls replaced in manager, worker, agents

### Pillar 5: Quality (Eval Harness)
- [x] **Golden Dataset** — `tests/golden_dataset.json` — 15 eval cases (5 easy, 5 medium, 5 hard) across 4 categories
- [x] **LLM-as-a-Judge** — 5-point rubric for Groundedness, Relevance, Task Success
- [x] **Behavioral Diffing** — `compare_runs()` detects silent regressions between versions
- [x] **CLI Utility** — `tests/run_evals.py` with `--filter`, `--difficulty`, `--output`, `--compare`
- [x] **Pass Rate Threshold** — exit code 1 if < 80% pass rate

### Pillar 6: Resilience (Circuit Breaker & Serialization)
- [x] **MissionSnapshot** — `squad_os/models/snapshot.py` — full state serialization with reasoning_trace
- [x] **Interrupt/Resume** — `squad_os/core/snapshot.py` — capture and restore mission state
- [x] **Quality Circuit Breaker** — `squad_os/core/circuit_breaker.py` — 3-failure threshold prevents silent degradation
- [x] **Async DB Pool** — `squad_os/core/db_pool.py` — WAL mode, `busy_timeout`, `retry_on_locked` with exponential backoff
- [x] **ProjectBranch** — `squad_os/core/projects.py` — isolated workspaces per mission

### Pillar 7: Human Oversight (Resilient HITL UI)
- [x] **Streamlit Fragments** — `@st.fragment(run_every=5000)` on HITL queue — eliminates full-script reruns
- [x] **Centralized Interrupt Resolution** — `_resolve_interrupt()` — single source of truth for approve/reject/resume
- [x] **Budget Display** — progress bars for token/turn/cost usage in HITL queue
- [x] **Safety Screening** — input guardrails applied at dashboard submission
- [x] **Duplicate Removal** — eliminated duplicate `approve_tool_interrupt` and `reject_tool_interrupt` functions

### Deliverables
- `squad_os/core/sandbox.py` — Docker executor for T3/T4 tools
- `squad_os/core/guardrails.py` — input safety screening
- `squad_os/core/context.py` — context window management
- `squad_os/core/logging.py` — structured logging with correlation IDs
- `squad_os/core/evals.py` — evaluation harness and LLM-as-a-Judge
- `squad_os/core/circuit_breaker.py` — quality-aware circuit breaker
- `squad_os/core/db_pool.py` — async connection pool with retry
- `squad_os/core/snapshot.py` — state serialization and restore
- `tests/golden_dataset.json` — 15-case eval dataset
- `tests/run_evals.py` — CLI eval runner
- `tests/test_sandbox.py` — sandbox + fallback tests
- `tests/test_context.py` — context pruning tests
- `tests/test_guardrails.py` — input screening tests
- `dashboard.py` — refactored with Fragments + centralized interrupts
- `worker.py` — structured logging + safety screening

---

## Notes

- Codebase migrated from TypeScript to Python (`squad_os/` package)
- System uses SQLite (`shared_memory.db`) with WAL mode for concurrent access
- Worker polls queue every 5s; dashboard uses Streamlit Fragments for HITL polling
- All 7 production-readiness pillars implemented and tested
- Memory files (`memory/YYYY-MM-DD.md`) track daily decisions and context
- Run `python worker.py` to activate the worker; `streamlit run dashboard.py` for UI

---

_Last updated by Axiom on 2026-05-18_
