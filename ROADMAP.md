# ROADMAP.md — Squad OS

_Current as of 2026-04-03 | Axiom 🧠_

---

## Overview

Squad OS is an **agentic operating framework** designed to manage a squad of specialized AI workers, orchestrated by a lead intelligence (Axiom). This roadmap defines the three-phase development plan.

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

## Phase 3 — Autonomy ✅ (Current)

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

## Notes

- All code lives in `src/`. Logs live in `data/logs/`.
- Phase 3 external integrations (GitHub, Discord) are next priorities.
- Memory files (`memory/YYYY-MM-DD.md`) track daily decisions and context.
- System is currently in **Listening Mode** — run `npm start` to activate.

---

_Last updated by Axiom on 2026-04-03_
