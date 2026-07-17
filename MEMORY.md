# MEMORY.md — Long-Term Memory

## Who I Am

I'm the lead intelligence for **Squad OS**, an autonomous multi-agent engineering OS. I work with **John Rey** (GMT+8, Asia/Singapore). We build self-correcting AI systems that decompose goals, delegate to specialized agents, write code, test it, and deploy it — all without human hand-holding.

## The Stack

- **Worker runtime**: `start_worker.py` polls every 3s on `shared_memory.db` for `QUEUED` missions
- **LLM**: `ollama/gemma4:31b-cloud` with `$5.00 / 500k token` budget via `TokenBudget`
- **Platform**: Windows, Python 3.11, Streamlit dashboard on `:8501`
- **Agents**: Router → Planner → Task agents (3+ specialists per mission) → Verifier → Committer
- **Datastore**: SQLite via `aiosqlite` at `shared_memory.db` (root of workspace)

## What's Hardened (July 2026 Architecture Sprint)

### Mandatory Gate Enforcement
Gates are NOT optional. The planner writes them into task JSON plans; the verifier reads them from there. The LLM never controls which gates run.

**Gate types**: `TestGate` (pytest), `LintGate` (ruff), `TypeCheckGate` (mypy), `FileExistsGate`, `OutputKeywordGate`

**Key fixes**:
- `GateSuite.__init__`: empty list loads defaults (`if not gates` fixes silent skip)
- `filter_by_names()` normalizes name variants (`ruff`→`lint`, `mypy`→`type_check`)
- Empty gate results = explicit failure when gates were requested
- Module-not-found = graceful skip, not crash

### Workspace Fallback Chain
Tasks that call `commit_project` archive the workspace before the verifier runs. The verifier resolves via 3-level fallback:
`task_workspace → project_path → archive directory`

If none exist, it skips file gates silently for meta-tasks.

### Worker Health
`start_worker.py` marks missions `COMPLETED` after `run_mission()` succeeds (fixes infinite re-queue loop). Agent task-level isolation uses per-task subdirectories.

### Dashboard
Streamlit dashboard at `localhost:8501` with:
- 5-column Metric Ribbon (Cost, Tokens, Success Rate, Active, Total)
- Pipeline Tab — Graphviz DAG with native HTML/CSS fallback when `dot` not in PATH
- `@st.fragment` per-task log streams

### Testing
- 70 unit tests all passing
- Mission #23 (async web scraper, 5-agent delegation): 5/5 tasks, 0 fails, gates live-passing
- All 7 missions in DB are COMPLETED or FAILED — no hanging tasks

### Repository
- Pushed to remote GitHub, fully synced
- Worker idles on 3s poll. New missions can be queued at any time.
