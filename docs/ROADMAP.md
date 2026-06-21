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
- EEG capture and EEG-BIDS export
- ROS 2 / rosbag2 export
- Motion-BIDS export — **in progress (single-session export landed)**
- IK / robot-arm replay (beyond mocap spheres)
- Consent *filtering* — strip disallowed modalities from a release while still including the session — **in progress (modality filtering landed)**
- Multi-session queryable catalog
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
- ROS 2 / rosbag2 (deferred; export adapter planned)
- IK/robot-arm replay (mocap spheres prove round-trip; arm kinematics in v0.2)
- Multi-session catalog (single-session pipeline is enough for v0.1 trust claim)
