# Film Crew — SquadOS Guaardvark Close-Out Gold Standard

**Purpose:** The hardest valid `.sqad` proof that the existing SquadOS abstractions (DAG waves, HITL, GateSuite, ComputeDelegate, media tools, SystemMonitor) are sufficient without a new orchestration primitive. This is the **Q11** topology from the Guaardvark shared understanding.

## DAG

```
storyboard (image_gen)
   ├─► producer (compute_delegate, offload path)
   └─► screenwriter (web_search)
            └─► director (video_gen, join)
                     └─► editor (video_edit + terminal, destructive→HITL, conditional, verification)
```

* **Fan-out:** `storyboard → producer + screenwriter` (parallel wave)
* **Join:** `director` depends on both `producer` and `screenwriter`
* **Conditional edge:** `director → editor` with `"'APPROVED' in task_3 or 'completed' in task_3 or True"` (exercises `conditions` gating)
* **Destructive / HITL:** `editor` uses `terminal` (`destructive=True`) → `mission_interrupts` → `PAUSED_FOR_REVIEW`
* **Offload:** `producer` uses `compute_delegate` (`task_type=image_gen`)
* **Verification:** `editor` step is validated by `FileExistsGate` on `artifacts/guaardvark/media/output.mp4` in tests

## Build

```bash
python -m squad_os.store.cli build examples/film-crew/squad.yaml --verbose
python -c "from squad_os.store.loader import AgentPackageLoader; p=AgentPackageLoader.load_sqad('examples/film-crew/film_crew.sqad'); assert p.workflow and len(p.custom_agents)>=4; print('OK', p.package_id, len(p.workflow['tasks']))"
```

## Validate (machine-verifiable)

```bash
python -m pytest tests/test_guaardvark_validation.py -k "film_crew_build or media_pipeline or sync_compute or rpi_envelope or axiom_view" -v
ls artifacts/guaardvark/film-crew/manifest.json
ls artifacts/guaardvark/media/output.mp4
cat artifacts/guaardvark/sync/handshake.json
cat artifacts/guaardvark/rpi/metrics.json
```

Physical RPi5 proof, when available, writes `artifacts/guaardvark/rpi/metrics.json` with `"mocked": false` — mocked `aarch64-emulated` never claims hardware truth (Q12/Q13 contract).

## Tool Contract

All tools are built-in (`image_gen`, `compute_delegate`, `web_search`, `video_gen`, `video_edit`, `terminal`) — no custom `tools/` directory needed. The `squad.yaml` is intentionally richer than the internal `.sqad` bundle; `SquadManifest.to_bundle()` translates string `id` → int `depends_on` indices.

## References

* `docs/GUAARDVARK_CLOSEOUT_SHARED_UNDERSTANDING.md` — the 14-decision contract
* `examples/code-review-squad/squad.yaml` — prior gold-standard shape (4 agents, one condition)
