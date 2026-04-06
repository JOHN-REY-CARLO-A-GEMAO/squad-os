---
name: SquadOS Reliability and Performance Upgrades
description: Design for improving JSON parsing, parallel execution, HITL recovery, and semantic role matching in SquadOS.
type: project
---

# SquadOS Reliability and Performance Upgrades Design

## 1. Robust JSON Parsing & Validation
**Goal**: Eliminate "hallucination" errors during recruitment and planning.

### Architecture
- **Pydantic Models**: Use `MissionPlan`, `TaskPlan`, and a new `SquadHirePlan` for strict schema enforcement.
- **The Validation Loop**:
    1. Request JSON via `litellm`.
    2. Validate using `pydantic.TypeAdapter(Model).validate_json(content)`.
    3. **On Failure**: Capture the `ValidationError`, append it to the prompt as a "Correction Request," and retry up to `max_retries`.
    4. **On Exhaustion**: Trigger HITL recovery.

### Data Flow
`LLM Response` $\rightarrow$ `Pydantic Validation` $\rightarrow$ `(Success: Proceed / Failure: Append Error $\rightarrow$ Retry)`

---

## 2. Parallel Task Execution (Explicit Dependency Mapping)
**Goal**: Reduce total mission time by executing independent tasks concurrently.

### Architecture
- **Schema Update**: Add `depends_on: List[int] = []` to `TaskPlan` (indices of prerequisite tasks).
- **Execution Engine**:
    - Track task status: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`.
    - Use an `asyncio` task queue to manage concurrency.
- **The Scheduler**:
    - Continuously identify `PENDING` tasks whose `depends_on` prerequisites are all `COMPLETED`.
    - Launch these tasks concurrently using `asyncio.create_task()`.
- **Context Handling**: Instead of a global string, each task receives the concatenated outputs of its specific dependencies.

---

## 3. Human-in-the-Loop (HITL) Recovery
**Goal**: Prevent token waste and crashes by allowing manual intervention.

### Architecture
- **The Interrupt**:
    1. Trigger on critical failure (e.g., Pydantic retries exhausted).
    2. Set mission status to `PAUSED_USER_INPUT`.
    3. Save state (task index, context, error) to a new `mission_interrupts` SQLite table.
- **User Interaction**:
    - Streamlit dashboard displays the error and provides a text input for "Guidance."
- **The Resume**:
    - Manager reads user guidance, injects it as a high-priority system instruction, and resumes from the failed task.

---

## 4. Semantic Role Matching
**Goal**: Accurately match requested roles to hired agents using semantic similarity.

### Architecture
- **Embedding Model**: Use `sentence-transformers` with the `all-MiniLM-L6-v2` model for lightweight, local embeddings.
- **Matching Logic**:
    - Calculate **Cosine Similarity** between the embedding of the requested role and the embeddings of all hired roles.
    - If similarity $\ge 0.85$, it is a match.
- **Fallback**: If no match is found, trigger the HITL recovery mechanism to ask the user for a manual assignment.

---

## Summary of Changes

| Component | Change | Target File |
| :--- | :--- | :--- |
| `Manager` | Implement Pydantic loop, `asyncio` scheduler, HITL logic | `squad_os/orchestrator/manager.py` |
| `Models` | Add `depends_on` to `TaskPlan`, create `SquadHirePlan` | `squad_os/orchestrator/manager.py` |
| `Database` | Add `mission_interrupts` table | `squad_os/database/session.py` |
| `Agents` | Integrate `sentence-transformers` for role matching | `squad_os/agents/base.py` |
