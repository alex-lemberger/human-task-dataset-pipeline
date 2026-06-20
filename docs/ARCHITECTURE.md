# Architecture

Human-Task Dataset Pipeline v0.1 — filesystem-only, offline, deterministic.

## Layers

```
synth ─▶ raw/ ─▶ validate ─▶ process ─▶ processed/ ─▶ qc ─▶ package ─▶ releases/ ─▶ replay
                    │                                    │        │
                 schemas                             defects   consent gate
                (pydantic)                           caught    (block-on-conflict,
                                                     (warn)    atomic staging)
```

### Data tiers

| Tier | Path | Immutable? | Description |
|------|------|-----------|-------------|
| raw | `data/raw/<sid>/` | Yes — checksummed | Written once by `synth` or a future `ingest` step. Never modified by downstream stages. |
| processed | `data/processed/<sid>/` | No — regenerable | Parquet output of `process`; `qc_report.json` and `qc_report.html` added by `qc`. |
| releases | `data/releases/<name>/` | Yes — atomic | Written atomically by `package`; includes consent manifest and checksums. |

### Module layout

```
src/htdp/
  schemas/      # Pydantic models (Session, Consent, DeviceConfig, Manifest, …) + JSON Schema export
  synth/        # Seeded synthetic session generator with deliberate defect injection
  io/           # Raw read/write helpers, checksums, atomic staging
  validate.py   # Schema + structure + checksum validation
  processing/   # extract → Parquet (raw is read-only)
  qc/           # Per-stream and cross-stream checks, HTML/JSON report
  consent/      # Consent model, release profiles, export gate
  release/      # Release packaging, manifest, release manifest
  replay/       # MuJoCo mocap-body player (optional dependency: extra "replay")
  cli.py        # Typer CLI — the only product surface
```

## CLI surface

```
htdp synth      --seed N --out data/raw/<id> [--force]
htdp validate   data/raw/<id>
htdp process    data/raw/<id>
htdp qc         data/processed/<id>
htdp package    <id...> --release <name> --profile <profile>
htdp replay     data/releases/<name>
```

## Design constraints (v0.1)

- **No servers** — Postgres, MinIO, FastAPI, Docker are all deferred to v0.2.
- **No real hardware** — no VIVE, LSL, XDF, EEG, video capture.
- **No ROS** — rosbag2 export deferred to v0.2.
- **Deterministic** — seeded generator, canonical serialization (§ Reproducibility).
- **Testable** — all stages have pytest coverage; replay is gated on optional MuJoCo dep.

## Reproducibility

Same code + `uv.lock` + platform + seed + inputs → identical release-manifest checksums.
Tool versions are recorded in the manifest but excluded from the reproducibility hash so
the check is stable across machines with different Python patch versions.

See `docs/DATA_CONTRACT.md` for canonical serialization rules and column specifications.
