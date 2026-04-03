# ROADMAP.md — Squad OS

_Current as of 2026-04-03 | Axiom 🧠_

---

## Overview

Squad OS is an **agentic operating framework** designed to manage a squad of specialized AI workers, orchestrated by a lead intelligence (Axiom). This roadmap defines the three-phase development plan.

---

## Phase 1 — Foundations ✅ (Current)

**Goal:** Establish the core infrastructure and prove the system works.

### Objectives
- [x] Initialize repository with TypeScript/Node.js
- [x] Set up directory structure (`src/core`, `src/agents`, `src/tools`, `data/logs`)
- [x] Create identity and operating manifesto
- [x] Establish memory and logging conventions
- [ ] Build `pulse.ts` — the heartbeat script
- [ ] Define core orchestration primitives in `src/core`

### Deliverables
- `package.json` with TypeScript, tsx, @types/node
- `tsconfig.json` (strict mode, ES2022)
- `docs/squad/MANIFESTO.md`
- `src/core/pulse.ts` — Squad OS heartbeat
- `data/logs/` — persistent execution log directory

---

## Phase 2 — Agentic Swarm

**Goal:** Move from single-threaded execution to a multi-agent dispatch system.

### Objectives
- [ ] Build a **Dispatcher** agent in `src/agents/dispatcher.ts`
  - Understands high-level goals and breaks them into sub-tasks
  - Maintains a task queue with status tracking
- [ ] Create specialized **Worker** agents:
  - `src/agents/coder.ts` — writes, refactors, and debugs code
  - `src/agents/researcher.ts` — gathers info, reviews docs, validates outputs
- [ ] Implement **agent communication protocol** (message-passing between agents)
- [ ] Build a **task manifest** (`data/logs/tasks.json`) — live tracking of all sub-tasks
- [ ] Add basic CLI commands to spawn/destroy workers

### Deliverables
- `src/agents/dispatcher.ts` — task orchestrator
- `src/agents/coder.ts` — code-focused worker
- `src/agents/researcher.ts` — research-focused worker
- Task queue with status: `pending`, `in-progress`, `done`, `blocked`
- Worker spawning via CLI

---

## Phase 3 — Autonomy

**Goal:** Squad OS runs with minimal supervision, corrects itself, and integrates with the outside world.

### Objectives
- [ ] **Background processes** — long-running agents that monitor and act
- [ ] **Self-correction loop** — agents that review their own outputs and retry on failure
- [ ] **External integrations:**
  - GitHub API (PR creation, issue tracking, repo management)
  - Discord webhook (status reports, alerts)
  - Filesystem watcher (auto-reaction to file changes)
- [ ] **Persistence layer** — SQLite or JSON-based store for agent state
- [ ] **Self-healing** — automatic recovery from known failure modes
- [ ] **Dashboard** — simple HTML status page showing squad health

### Deliverables
- Background worker daemon
- Self-correction/retry logic
- GitHub integration (Issues + PRs)
- Discord webhook notifier
- Agent state persistence
- Web-based status dashboard

---

## Notes

- All code lives in `src/`. Logs live in `data/logs/`.
- Phase 3 external integrations are speculative — may be refined based on actual needs.
- Memory files (`memory/YYYY-MM-DD.md`) track daily decisions and context.

---

_Last updated by Axiom on 2026-04-03_
