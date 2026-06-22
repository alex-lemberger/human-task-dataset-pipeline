# AGENTS.md — Human-Task Dataset Pipeline (v0.1)

This project is a **consent-based human-task dataset pipeline for robotics**. The
product unit is a **dataset release**, not an app. v0.1 is a synthetic, filesystem-only
spine.

## Hard rules
- Do NOT add servers (Postgres/MinIO/FastAPI), Docker, dashboards, real hardware,
  LSL/XDF, video, EEG, ROS, or IK/robot replay in v0.1.
- Do NOT store raw data in a database.
- Do NOT bypass consent checks. `package` blocks on conflict and writes nothing.
- Do NOT modify raw data during processing. Raw is immutable.
- `htdp ingest-video` re-writes `device_config.json` and `checksums.sha256` of an
  existing raw session as a **raw-construction** step (populating the `video/`
  slot), which is distinct from the prohibited *processing-stage* mutation of raw.
- Keep fixtures tiny and deterministic. Update schemas and docs together.
- Preserve manifests + checksums. Make errors explicit.

## Quality gate (run before every commit)
`uv run ruff format --check . && uv run ruff check . && uv run pytest`
Typecheck: `uv run mypy src/htdp/schemas src/htdp/consent src/htdp/release src/htdp/io src/htdp/ingest src/htdp/export`

## Reproducibility
Same code + uv.lock + platform + seed + inputs → identical release-manifest checksum.
Canonical JSON (sorted keys, UTF-8) and CSV (stable columns, 6dp floats, \n). Generated
timestamps seed-derived; tool versions recorded but excluded from the reproducibility hash.

## Skills

Applicable: `superpowers:brainstorming`, `superpowers:writing-plans`,
`superpowers:test-driven-development`, `mujoco-python`.

Ignore: `angular-developer`, `wordpress-divi-admin`, `figma:*`.

## Scope (v0.1 boundary)

v0.1 must remain **offline, deterministic, synthetic, filesystem-only, and testable on a
normal development machine**. Any change introducing real hardware, servers, dashboards,
ROS, EEG, or video is **out of scope** and must be rejected unless this spec is
intentionally revised.

## Architecture summary

```
ingest (xdf → raw/, optional) | synth → raw/ → validate → process → processed/ → qc → package → releases/ → replay
```

Three data tiers on disk:
- **raw/** — immutable once written, checksummed.
- **processed/** — regenerable (Parquet + QC report).
- **releases/** — versioned, packaged. The product unit.

CLI is the only product surface. No server processes, no dashboard.

Usage:
- `uv sync --extra ingest` (install pyxdf optional dependency)
- `htdp ingest <file.xdf> <ingest.json> --out data/raw`
- The `ingest.json` sidecar `ingest_map` supports roles: `motion`, `events`, and `eeg`. An eeg entry shape: `{"role":"eeg","eeg_id":<id>,"channels":{<label>:<index>,...}}`.
- `htdp ingest-video <session_dir> <clip.mp4> <video.json> [--force]`
- `htdp synth --out data/raw`
- `htdp validate data/raw/<session_id>`
- `htdp process data/raw/<session_id>`
- `htdp qc data/processed/<session_id>`
- `htdp package --release <name> --profile <profile> <session_ids...>`
- `htdp replay data/releases/<name>`
- `htdp export-bids <raw_dir> <out_dir> [--force]` (**read-only export**; writes a separate BIDS tree, never mutates raw/processed/releases)

## Extending the project

- To add a new backend or data source, **do not touch existing pipeline stages**. Add a
  new stage or an adapter before the raw tier.
- Changing a schema model requires updating `docs/DATA_CONTRACT.md` and the JSON schemas
  (`uv run python -c "from pathlib import Path; from htdp.schemas.export import
  export_json_schemas; export_json_schemas(Path('docs/schemas'))"`).
- The `replay` extra (`mujoco`) is optional. Core tests must pass without it.
- New CLI commands go in `src/htdp/cli.py`; business logic goes in a matching submodule.
