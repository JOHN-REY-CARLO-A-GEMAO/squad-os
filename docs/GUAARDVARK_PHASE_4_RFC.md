# Guaardvark Phase 4 RFC — Real Infrastructure Validation

**Status:** Draft RFC — documentation only, no code in this commit  
**Frozen close-out:** `guaardvark-software-close-out` → `da0ef88` (148/148 regression, 6/6 mocked Guaardvark gates, genuine conditional `"'APPROVED' in task_3"`, 0 new tables/branches)  
**Purpose:** Define exactly what turns each 🟡 (mocked) into `mocked:false` evidence without reopening the architecture. Phase 4 does not invent a new orchestration primitive — it *measures* the frozen one under real infra.

> **Rule:** "Degrade, don't invent" stays. If Phase 4 needs >2 new branches in `Manager.execute_dag()` or a new SQLite table, stop and write an ADR — do not sneak it into close-out.

---

## 1. Scope — What Phase 4 Is and Is Not

**Is:** A validation/research phase that replaces `mocked:true` artifacts with `mocked:false` captures on real hardware/network/GPU, using the same `examples/film-crew/squad.yaml`, `squad_os/api/axiom_view.py`, and `tests/test_guaardvark_validation.py` interfaces. Each item below is a *separate* evidence run; failures are isolated per Q6 containment.

**Is not:** A new feature sprint. No new DAG engine, no distributed queue, no SQLite replacement, no `dashboard.py` rewrite. Any such proposal requires a new ADR and a new tag.

**Where evidence lives:** Same `artifacts/guaardvark/<capability>/{*.json,*.mp4}` paths, but with `mocked:false` and a `hardware:` block. The CI gate stays `python -m pytest -q --ignore=tests/test_visual_tools.py` (148 passed) plus `python -m pytest tests/test_guaardvark_validation.py -v` (6 mocked). Phase 4 real runs are *additional* jobs that upload `mocked:false` artifacts — they do not gate the close-out tag.

---

## 2. Yellow → Green: Required Real Evidence

| # | Phase 4 item | Required `mocked:false` evidence | How to capture (reproducible) | Pass gate |
|---|---|---|---|---|
| **1** | **2-host Zeroconf discovery** (`_squados._tcp.local.`) | Two *actual* hosts (x86_64 + second host or RPi5) discover each other via `SquadDiscoverTool`. Artifact `artifacts/guaardvark/sync/handshake_real.json` with `mode:"real"`, `mocked:false`, `discovery_ms`, `nodes[].host` as two distinct IPs, `zeroconf` service `_squados._tcp.local.` visible on both. | On host A: `SQUAD_SYNC_URL=http://<hostB>:8900 python -c "from squad_os.tools.sync import SquadDiscoverTool; …"` after `avahi-daemon`/`zeroconf` running. Measure `time.time()` around `await discover.execute(timeout=5)`. Require `<5 s` (Q7). Persistence: `handshake_real.json` with both IPs. | `discovery_ms < 5000` and `len(nodes) >= 2` with distinct `host` |
| **2** | **10 MB network delegation** | Real `ComputeDelegateTool` transfer of ≥10 MB payload over LAN (not loopback `mocked aiohttp`). Artifact `handshake_real.json` `delegate_ms`, `bytes:10000000`, `node` as real hostB, `result` from hostB execution. | `payload={"data": "x"*1024, "bytes": 10_000_000, "note": "phase4 real"}`; `await delegate.execute(task_type="image_gen", payload=payload, timeout=30)` with `SQUAD_SYNC_URL` pointing to hostB running a real `SquadSync` delegate server. Measure `<30 s p95` (Q7). | `delegate_ms < 30000` and `result.bytes == 10000000` |
| **3** | **RPi5 ARM64 hardware + thermal** | Actual `aarch64` hardware (`platform.machine()=="aarch64"`, `mocked:false`), `SystemMonitorTool(metric="all")` capture showing `idle RAM <512 MB` equivalent (`available_gb` semantics) and thermal `<85°C` under a real 3-agent swarm. Artifacts `rpi/metrics_real.json` + `rpi/thermal_trace.json`. | On RPi5: boot with active cooling, `python start_worker.py` + 3-agent Film Crew mission (storyboard→producer→director) running, poll `SystemMonitorTool` every 5 s, record `sensors_temperatures()` trace for swarm duration. | `available_gb > 0.5` (idle envelope) and `max(temp.current) < 85` for 10 min swarm |
| **4** | **Media real `diffusers` + `ffmpeg` + `ffprobe`** | Real `ImageGenTool(model=flux/sdxl-turbo)` → image file exists, `VideoGenTool(mode=image_to_video)` → mp4, `AdvancedVideoEditorTool(action=stitch)` → `output.mp4` ~1 s, `ffprobe` duration ≈1.0 s. Artifacts `media/output_real.mp4` (`ffprobe_real:true`, `mocked:false`) + `media/ffprobe_real.json`. | On GPU host (CUDA): `pip install diffusers torch --index-url https://download.pytorch.org/whl/cu121`, run mocked-pipeline test but with `IMAGE_GEN_MOCK=0` so `ImageGenTool._generate_local` loads `black-forest-labs/FLUX.1-schnell` (4 steps) and `ffmpeg` is installed (`apt install ffmpeg`). `ffprobe -show_entries stream=duration -of json`. | `output_real.mp4` exists, `ffprobe.streams[0].duration` in `0.9..1.1` |
| **5** | **Concurrency production workload** | Production workload that demonstrates the Q7 CPU/memory guard: under `CPU >80%` or `mem >75%`, `SQUAD_OS_LLM_CONCURRENCY` drops 5→2 without a new subsystem. Artifact `rpi/concurrency_trace.json` with `concurrency` timeline + `system_detail` trace. | Add the single `if` in `Manager` pre-wave (deferred in close-out) — `if psutil.cpu_percent() >80 or psutil.virtual_memory().percent >75: concurrency=2`. Run swarm under `stress-ng` CPU load, log `Manager` wave logs + `SystemSummaryTool`. | `concurrency==2` observed when guard tripped, and `PAUSED_FOR_REVIEW` not starved |

---

## 3. How Phase 4 Evidence Differs from Mocked (Q8/Q12)

* **Mocked** (close-out, `da0ef88`): `platform.machine→aarch64` via `monkeypatch`, `psutil` shim, `aiohttp` fake, Pillow→stub MP4, `mode:loopback`/`mocked:true`, `ffprobe_real:false`. Proves *interface + timing envelope*, not hardware.
* **Real** (Phase 4): same `tests/test_guaardvark_validation.py` but with flags `GUAARDVARK_REAL=1`, `mocked:false`, `mode:real` or `physical`, `hardware:{arch, temp_trace, nodes:[hostA,hostB]}`. Proves hardware. The two must never be conflated — a real run is a *new* artifact, not an overwrite of mocked.

---

## 4. Reproduction (Phase 4, when hardware available)

```bash
# Close-out stays green (frozen)
git rev-parse guaardvark-software-close-out  # → da0ef88
git rev-parse HEAD                           # → newer if RFC committed
python -m pytest -q --ignore=tests/test_visual_tools.py  # 148 passed (frozen gate)

# Real runs (examples, not run on CI)
# 1. Two-host Zeroconf
SQUAD_SYNC_URL=http://192.168.1.101:8900 python -m pytest tests/test_guaardvark_validation.py::test_sync_compute_real -v
cat artifacts/guaardvark/sync/handshake_real.json  # mocked:false, nodes:2

# 2. RPi5
ssh pi@rpi5 "python -m pytest tests/test_guaardvark_validation.py::test_rpi_envelope_real -v"
cat artifacts/guaardvark/rpi/metrics_real.json     # mocked:false, arch:aarch64

# 3. Media (GPU host with ffmpeg)
apt install ffmpeg && pip install diffusers torch accelerate
GUAARDVARK_REAL=1 python -m pytest tests/test_guaardvark_validation.py::test_media_pipeline_real -v
ffprobe -v error -show_entries stream=duration -of json artifacts/guaardvark/media/output_real.mp4
```

---

## 5. Non-Goals for Phase 4 (still out)

* No distributed SQLite replacement, no new `mission_interrupts` table, no distributed lock.
* No `dashboard.py` rewrite — Axiom View stays `htdocs/axiom-view/index.html` + `GET /api/v1/axiom-view` RO.
* No cloud GPU service — Phase 4 delegate is LAN `SQUAD_SYNC_URL`, not a cloud API.

If any of these become necessary, write `docs/ADR-guaardvark-distributed-primitive.md` per Q9 Tripwire 2 and re-estimate — do not patch `da0ef88`.

---

*Author: Axiom · Date: 2026-09-14 · Branch: `arena/01a09d3b-squad-os` after `guaardvark-software-close-out`*
