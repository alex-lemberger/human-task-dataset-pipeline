# Roadmap

## v0.1 — Synthetic spine (complete)

The first milestone proves the *factory* works before any hardware exists.

**Done:**
- Python package + `uv`/`ruff`/`mypy`/`pytest` tooling
- Pydantic schemas + JSON Schema export (`docs/schemas/`)
- Seeded synthetic session generator with deliberate defect injection (dropped-sample gap + clock drift)
- Checksum-based immutability enforcement (`checksums.sha256`)
- Schema + structure + checksum validation (`htdp validate`)
- Processing pipeline: raw CSV → Parquet (`htdp process`, raw read-only)
- QC report: per-stream + cross-stream checks, pass/warn/fail severity, JSON + HTML output (`htdp qc`)
- Consent gate: block-on-conflict, three release profiles, atomic staging (`htdp package`)
- Reproducibility: identical release-manifest checksums across two runs
- MuJoCo mocap-body replay from the packaged release (optional dep, smoke-tested headless) (`htdp replay`)
- IK / robot-arm replay (beyond mocap spheres): differential IK with mink+daqp, vendored 6-DOF arm (`htdp replay-ik`), trajectory export to CSV (`--out`), full-pose orientation tracking (`--orientation-cost`)
- AGENTS.md harness instructions
- Docs: ARCHITECTURE, DATA_CONTRACT, ETHICS_AND_CONSENT, this ROADMAP
- Protocol: `protocols/reach-grasp-place.md`

---

## v0.2 — Real hardware ingest (planned, not started)

**Deferred from v0.1:**
- Postgres / MinIO / FastAPI / Docker Compose
- Angular operations dashboard
- Real hardware: VIVE tracker capture, LSL streaming, XDF ingest (`htdp ingest`: XDF → raw representation) — **in progress (XDF adapter landed)**
- Video capture (MP4 population in the `video/` slot) — **in progress (ingest-video landed)**
- EEG capture — **in progress (XDF eeg ingest landed; EEG-BIDS export landed)**
- ROS 2 / rosbag2 export — **done** (motion + events + EEG via `htdp export-release-rosbag`)
- Motion-BIDS export — **done** (single-session + multi-subject release-level export)
- Consent *filtering* — strip disallowed modalities from a release while still including the session — **done (per-session granularity landed; modality files dropped only from sessions whose consent forbids them)**
- Multi-session queryable catalog — **done** (`htdp catalog` + `htdp catalog-query` with range filters landed; release-level inventory via `htdp catalog-releases` landed)
- Agent-orchestration layer (Hermes / OpenClaw)
- Remote / multi-user access

**Guiding principle for v0.2:** add one real modality at a time. Each modality adds an
`ingest` adapter that normalizes to the existing raw representation — the downstream
pipeline (validate → process → qc → package) must not change.

---

## Out of scope (named, not forgotten)

The following were considered and explicitly deferred — not missed:

- Postgres, MinIO, FastAPI, Docker in v0.1 (no concrete reason yet; filesystem suffices)
- LSL/XDF in v0.1 (a planned `ingest` step will bridge it; raw-as-CSV is intentional)
- Video and EEG (schema slots exist; data capture deferred)
- ROS 2 / rosbag2 — **done** for motion + events + EEG (`htdp export-release-rosbag`)
- IK/robot-arm replay — **done** (mocap spheres via `htdp replay`, differential IK + trajectory export via `htdp replay-ik --out`, orientation tracking via `--orientation-cost`)
- Multi-session catalog (single-session pipeline is enough for v0.1 trust claim)
