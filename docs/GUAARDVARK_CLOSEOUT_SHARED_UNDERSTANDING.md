# Guaardvark Close-Out — Shared Understanding

**Date:** 2026-09-14 (Asia/Singapore) · **Branch:** `arena/01a09d3b-squad-os` @ `304943c` · **Lead:** Axiom 🧠 + John Rey
**Skill:** `mattpocock/skills: grill-me → grilling` (output redirected to `/tmp/grill-output.txt`, supporting files `/tmp/skills-use-EMIEPT/grill-me` → `/tmp/skills-use-Rrn7CW/grilling`)
**Status:** `FRONTIER EMPTY` — grilled in 3 rounds (Q1–Q14 settled). **No code yet** — this doc is the gate before implementation.

---

## 1. Grill Target (Q1)

**Grill the decision to finish Guaardvark** by shipping the two missing deliverables and validating the three missing validations, not by expanding the architecture:

* **Ship:** Axiom View (RPi5 mini-screen) + Film Crew `.sqad` workflow
* **Validate:** RPi5 ARM64 envelope + media-mission e2e + two-node Sync/Compute
* This is a **close-out**, not a new pillar. `GUAARDVARK_ROADMAP.md` Phase 1–3 moves from `PARTIALLY COMPLETE` → `COMPLETE` only on machine-verifiable evidence.

## 2. Core Bet (Q2)

> **The existing SquadOS abstractions are sufficient for distributed and creative work; remaining work is integration and validation, not a new orchestration primitive.**

Concretely: `Manager.execute_dag()` wave loop + HITL `PAUSED_FOR_REVIEW` + `GateSuite` + `SquadDiscoverTool`/`ComputeDelegateTool` + `ImageGenTool`/`VideoGenTool`/`AdvancedVideoEditorTool` + `SystemMonitorTool` + `shared_memory.db` migrations are the substrate. If Film Crew cannot round-trip through them on one machine, the bet is falsified.

## 3. Invariants & Non-Goals (Q3)

**Non-goals (explicitly out):**
* No new orchestration primitive, no distributed queue/lock, no SQLite replacement, no new SQLite table/migration
* No TS resurrection (`src/core` remains archival)
* No cloud GPU infrastructure
* No major `dashboard.py` rewrite

**Invariants (must not break):**
* Local-first, no-API-key default (`ollama/gemma4:31b-cloud` via LiteLLM)
* HITL pause/review semantics: `BaseTool.destructive=True` on `TerminalTool`/`PythonRunnerTool`/`CommitProjectTool` → `mission_interrupts` row → `PAUSED_FOR_REVIEW` → wave-loop re-polls `get_task_interrupt()` → `APPROVED` prefix re-queues, else `FAILED`
* `GateSuite` enforcement (empty list loads defaults, `filter_by_names` normalizes `ruff→lint`, empty results = explicit failure when gates requested, graceful skip when `ruff`/`mypy` absent)
* `shared_memory.db` migration-safe (`PRAGMA journal_mode=WAL`, column-add migrations)
* `.sqad` contract unchanged: `manifest.json` + `workflow.json` + `agents/*.json` + `tools/*.py` + `assets/` + `requirements.txt` zip via `AgentPackageLoader.build_sqad_from_yaml`

## 4. Shipped Proof (Q4)

**Guaardvark is done only when a skeptic can verify without testimony, via repo commands.** Loom/demo is not proof.

Canonical harnesses (fact-checked against repo — no invented `npm` scripts):
* **Build:** `python -m squad_os.store.cli build <squad.yaml> [-o <out.sqad>] [--verbose]`
* **Test:** `python -m pytest -q --ignore=tests/test_visual_tools.py` (15 suites; `pytest` is the harness defined in `pyproject.toml`)
* **Worker/Dashboard:** `python start_worker.py` (3s poll) / `streamlit run dashboard.py` (`:8501`)
* Physical RPi5 proof is **explicitly distinguishable** from mocked ARM validation — mocked `arch: aarch64-emulated` never claims hardware truth.

## 5. Priority & Sequencing (Q5)

**Rule: highest architectural risk first.**

```
A → B: failing acceptance tests first → Film Crew → Axiom View → full validation
```

1. Scaffold `tests/test_guaardvark_validation.py` with 5 tests that *currently fail* (see §8).
2. Build **Film Crew** before Axiom View — Film Crew exercises fan-out, join, condition, destructive/HITL, offload, and gates. If it cannot pass on one x86_64 box, Axiom View is cosmetic.
3. Build **Axiom View** as a read-only projection (thin, ~2 days) once the workload works.
4. Run the three validations last — they are assertions over the two built packages.

## 6. Failure Modes & Containment (Q6)

**Degrade, don't invent.**

* RPi5 or two-node failure is **isolated**: failed capability recorded as `FAILED`/`SKIPPED` with evidence JSON in `artifacts/guaardvark/<capability>/`, other capabilities continue validating locally.
* DB stays local SQLite; `SquadBlackboardTool` remains KV-only, not a distributed queue.
* `ComputeDelegateTool` failure never poisons the mission; mock stub writes a proxy artifact and marks validation `SKIPPED` with reason.
* HITL stays `PAUSED_FOR_REVIEW` indefinitely; no silent bypass of the `APPROVED` prefix contract.

## 7. Resource Envelope (Q7)

**Test-measured ceilings, not docs:**

| Signal | Ceiling | Probe |
|---|---|---|
| Idle RAM (worker + DB, pre-mission) | **< 512 MB** | `SystemMonitorTool(metric="memory")` |
| Thermal | **< 85 °C** | `psutil.sensors_temperatures()` |
| mDNS discovery | **< 5 s** (½ the roadmap's 10s) | `SquadDiscoverTool(timeout=5)` loopback |
| 10 MB delegate | **< 30 s p95** | `ComputeDelegateTool(payload=10_000_000)` local delegate |
| LLM concurrency | **≤ 5**, auto-drops to **2** when CPU >80% or RAM >75% | one `if` in `Manager` pre-wave check (not a subsystem) |
| Partition | DAG stays `PAUSED_FOR_REVIEW`; dashboard badge → `OFFLINE` after **5 min** | `mission_interrupts.status==PENDING` age check |

## 8. Machine-Verifiable Acceptance (Q8)

**One verification mechanism: `pytest`.** Every capability has a reproducible test + persisted artifact (artifacts carry `mocked` flag).

| Capability | Command | Artifact | Pass Condition |
|---|---|---|---|
| **Film Crew `.sqad`** | `python -m squad_os.store.cli build examples/film-crew/squad.yaml --verbose` + `python -c "from squad_os.store.loader import AgentPackageLoader; p=AgentPackageLoader.load_sqad('examples/film-crew/film_crew.sqad'); assert …"` | `artifacts/guaardvark/film-crew/manifest.json` | ≥4 agents, workflow with `depends_on`, load succeeds |
| **Media e2e** | `pytest -k test_media_pipeline` | `artifacts/guaardvark/media/output.mp4` (1s valid MP4) | `FileExistsGate` + `ffprobe` duration ≈1s |
| **RPi5 envelope (mocked)** | `pytest -k test_rpi_envelope_mocked` | `artifacts/guaardvark/rpi/metrics.json` | `memory<512MB`, `temp<85°C`, `"mocked": true, "arch":"aarch64-emulated"` |
| **Two-node Sync/Compute** | `pytest -k test_sync_compute` | `artifacts/guaardvark/sync/handshake.json` | `discovery_ms<5000`, `delegate_ms<30000`, `"mode":"loopback"` |
| **Axiom View** | `pytest -k test_axiom_view` + `GET /api/v1/axiom-view` | `artifacts/guaardvark/axiom-view/snapshot.json` | read-only `SELECT` on `missions`/`tasks`/`mission_interrupts` + `SystemSummaryTool(minimal=True)` |

**If any `pytest` or `ls artifacts/guaardvark/**` fails, Guaardvark is not done.** Physical RPi5 run (when available) writes `artifacts/guaardvark/rpi/metrics.json` with `"mocked": false` and is never conflated with mocked.

## 9. Kill Criteria (Q9)

**Two tripwires — hit either → stop patching, write `docs/ADR-guaardvark-distributed-primitive.md`, re-estimate.**

* **Tripwire 1 — timebox:** 2 full working days on `SquadDiscover`/`ComputeDelegate` loopback without `discovery_ms<5s` & `delegate_ms<30s` after 3 meaningful attempts → **cut multi-node from Guaardvark done**, defer to new `GUAARDVARK_PHASE_4.md` RFC; ship Axiom View + Film Crew + single-node media as v1.
* **Tripwire 2 — complexity:** fixing validation requires **>2 new branches** in `Manager.execute_dag()`/HITL wave loop **or** any new SQLite orchestration table/migration.

Not sneaking a new primitive into the close-out is itself a success criterion.

## 10. Axiom View Surface (Q10)

**One static file + one read-only FastAPI route. No Streamlit fork, no dashboard rewrite.**

* **Path:** `htdocs/axiom-view/index.html` (<50KB vanilla JS, kiosk-friendly, `--kiosk http://localhost:8000/axiom-view/`) + `squad_os/api/axiom_view.py`.
* **Route:** `GET /api/v1/axiom-view?mission_id=last` → `{mission, tasks[], interrupts[], system}`.
* **Read-only guarantee:** `sqlite3.connect(DB_PATH, uri=True, check_same_thread=False)` with `?mode=ro&immutable=1`; tests assert only `SELECT` (via `sqlparse` or RO-open) — zero writes, zero new table.
* **Projection:** `missions(id, goal, status, workflow_json)`, `tasks(mission_id, description, assigned_agent, status, verification_status)`, `mission_interrupts(mission_id, task_idx, context, status, user_guidance)`, plus `SystemSummaryTool(minimal=True)`.

## 11. Film Crew Topology (Q11)

**`examples/film-crew/squad.yaml` — 5 agents, exercises the full bet surface:**

```yaml
spec_version: "1.0.0"
metadata: { name: "Film Crew", version: "1.0.0", author: "Axiom", description: "Storyboard → Producer → Director → Screenwriter → Editor pipeline with offload, conditionals, and HITL." }
topology:
  agents:
    - { id: storyboard, role: "Storyboard Artist", system_prompt: "Create storyboard frames. MUST use image_gen tool.", tools: [image_gen] }
    - { id: producer, role: "Producer", system_prompt: "Offload heavy render. MUST use compute_delegate with task_type=image_gen.", tools: [compute_delegate] }
    - { id: screenwriter, role: "Screenwriter", system_prompt: "Research narrative. MUST use web_search tool.", tools: [web_search] }
    - { id: director, role: "Director", system_prompt: "Animate storyboard. MUST use video_gen mode=image_to_video.", tools: [video_gen] }
    - { id: editor, role: "Editor", system_prompt: "Stitch and verify. MUST use video_edit action=stitch then MUST use terminal to ls.", tools: [video_edit, terminal] }
  dependencies:
    - { parent: storyboard, child: producer }
    - { parent: storyboard, child: screenwriter }
    - { parent: producer, child: director }
    - { parent: screenwriter, child: director }
    - { parent: director, child: editor, condition: "'APPROVED' in task_3" }
runtime: { required_tools: [{name: image_gen}, {name: compute_delegate}, {name: video_gen}, {name: video_edit}] }
```

Fan-out (storyboard→2), join (director), conditional edge, offload (`compute_delegate`), `destructive=True` (`terminal` → HITL), `verification_gates: ["FileExistsGate"]` on `artifacts/guaardvark/media/output.mp4`.

## 12. Mocking Harness (Q12)

**Mock at the boundary, assert on the seam, label artifacts.**

* **RPi:** monkeypatch *only* `psutil` + `platform.machine` + `psutil.sensors_temperatures`; call real `SystemMonitorTool(metric="memory")`; assert real JSON. Artifact includes `"mocked": true`.
* **Media:** monkeypatch `diffusers`/`moviepy` import boundary to write valid `frame.png` then assemble 1s blank MP4 via `ffmpeg -f lavfi -i color=c=black:s=320x240:d=1` — `FileExistsGate` + `ffprobe`.
* **Sync/Compute:** two `SquadDiscoverTool`/`SquadBlackboardTool` clients + `ComputeDelegateTool(payload=10_000_000)` against loopback `127.0.0.1:9xxx` (timeout 5); measured `discovery_ms`/`delegate_ms` into `handshake.json` with `"mode":"loopback"`. No self-asserting mock.

## 13. Filesystem & Artifact Contract (Q13)

* **Built `.sqad`:** `examples/film-crew/*.sqad` remains `.gitignore`'d (`*.sqad`); tests build to `tmp_path` and copy only `manifest.json` snapshot to `artifacts/guaardvark/film-crew/`.
* **Evidence:** `artifacts/guaardvark/<capability>/*.json|*.mp4` — add `!artifacts/guaardvark/` allowlist to `.gitignore` + keep `artifacts/guaardvark/.gitkeep`; on CI (`CI==true`) artifacts uploaded via `upload-artifact`, not committed as litter.
* **Temp DB:** each `test_guaardvark_*.py` uses `monkeypatch.setattr("squad_os.database.session_missions.DB_PATH", str(tmp_path / "test_shared_memory.db"))` + `await init_db()` — no mutation of repo `shared_memory.db`, safe for `pytest -n auto`.
* **Idempotency:** each test deletes `artifacts/guaardvark/<capability>/*` before write (overwrite, not append).

## 14. Integration Safety (Q14)

**One-line pre-merge guard:**

```bash
python -m pytest -q --ignore=tests/test_visual_tools.py
```

Must stay green; `tests/test_guaardvark_validation.py` is additive, not replacive.

* Reuse: `AgentPackageLoader.build_sqad_from_yaml` + DFS `validate_workflow` + AST security scan + `SkillRegistry.get_tool(bare-name)` fallback; `get_task_interrupt`/`mission_interrupts` + `SystemSummaryTool`.
* CI: `.github/workflows/ci.yml` runs `pytest` **and** `python -m squad_os.store.cli build examples/film-crew/squad.yaml --verbose` as separate steps (loader regressions isolated from DB regressions).
* Any new branch in `manager.py` HITL loop or new `session_missions.py` migration beyond Q7's one-`if` concurrency guard trips Q9 and fails review.

---

## Design Tree — Closed

```
✅ Q1 Target  ✅ Q2 Bet  ✅ Q3 Invariants  ✅ Q4 Proof
✅ Q5 Priority  ✅ Q6 Containment  ✅ Q7 Envelope  ✅ Q8 Acceptance  ✅ Q9 Kill
✅ Q10 Axiom View  ✅ Q11 Film Crew  ✅ Q12 Harness  ✅ Q13 Artifacts  ✅ Q14 Safety
─────────────────────────────────────────────────
FRONTIER EMPTY — shared understanding reached. Ready to implement.
```

## Next Step (not yet executed)

Upon user confirmation of this doc, implementation order per Q5:

1. Scaffold `tests/test_guaardvark_validation.py` (failing) + `examples/film-crew/squad.yaml` + `.gitignore` allowlist.
2. Make Film Crew build+load green, then media/media-sync mocked pipelines green.
3. Add `squad_os/api/axiom_view.py` + `htdocs/axiom-view/index.html` + `test_axiom_view` read-only gate.
4. Run `python -m pytest` + `python -m squad_os.store.cli build … --verbose` locally; commit artifact snapshots.

No code has been written in this grill session — this document is the contract.
