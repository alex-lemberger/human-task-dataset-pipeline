# Data Contract

This document is the authoritative reference for the folder layout, file naming, and
CSV/Parquet column specifications used by the Human-Task Dataset Pipeline v0.1.

---

## Folder convention

```
data/raw/<session_id>/
  session.json            # session metadata (Schema: Session)
  consent.json            # participant consent record (Schema: Consent)
  device_config.json      # stream declarations + coordinate frame (Schema: DeviceConfig)
  streams/
    motion_right_wrist.csv
    motion_left_wrist.csv
    motion_torso.csv
    motion_object.csv
    events.csv
  video/                  # empty slot in v0.1 (contract present, no MP4)
  notes.md
  checksums.sha256        # SHA-256 over all raw bytes (immutability proof)

data/processed/<session_id>/
  motion.parquet
  events.parquet
  qc_report.json
  qc_report.html
  manifest.json

data/releases/<release_name>/
  README.md
  LICENSE
  protocol.md
  participants.csv
  sessions.csv
  manifest.json
  checksums.sha256
  data/<session_id>/...   # copied raw streams (motion CSVs)
```

---

## Coordinate frame

Declared in `device_config.json`. All motion data must conform.

- Units: **meters** (position), **seconds** (timestamps).
- World frame: **right-handed**; x = participant right, y = forward, z = up.
- Rotations: **quaternion, order `w, x, y, z`**.

---

## Motion CSV columns

File: `streams/motion_<tracker_id>.csv`

| Column | Type | Description |
|--------|------|-------------|
| `timestamp_s` | float (6dp) | Time since session start, seconds |
| `tracker_id` | str | Tracker name (e.g. `right_wrist`) |
| `x_m` | float (6dp) | Position x, meters |
| `y_m` | float (6dp) | Position y, meters |
| `z_m` | float (6dp) | Position z, meters |
| `qw` | float (6dp) | Quaternion w |
| `qx` | float (6dp) | Quaternion x |
| `qy` | float (6dp) | Quaternion y |
| `qz` | float (6dp) | Quaternion z |
| `quality` | float (6dp) | Tracking quality 0–1 |
| `defect_tag` | str | Empty unless synthetically injected defect |

Canonical rules: stable column order, 6 decimal places, UTF-8, LF line endings.

---

## Event CSV columns

File: `streams/events.csv`

| Column | Type | Description |
|--------|------|-------------|
| `timestamp_s` | float (6dp) | Time since session start, seconds |
| `event_id` | str | Unique event identifier |
| `label` | str | `start`, `grasp`, `release`, `place`, or `stop` |
| `phase` | str | Protocol phase name |
| `source` | str | `synthetic` (generated) or `real` (ingested capture) |
| `confidence` | float (6dp) | Event detection confidence 0–1 |
| `notes` | str | Free text |

Event ordering invariant: `start < grasp < release < place < stop`. All events must
fall within the session time bounds.

---

## Pre-raw ingest step (`htdp ingest`)

Real LSL recordings (.xdf files) can be ingested into raw session folders using:

    htdp ingest <file.xdf> <ingest.json> --out data/raw/<session_id>

The `ingest.json` sidecar is a JSON file with keys:
- `session` — Session schema fields (participant, protocol, etc.)
- `consent` — Consent record
- `device_config` — DeviceConfig (frame, streams)
- `ingest_map` — stream/channel mapping (motion streams + events stream)
- `frame_transform` (optional) — `{"rotation": [w,x,y,z]}` to rotate data into contract frame; consumed by ingest but **not persisted** into `device_config.json`

The ingest adapter writes canonical raw folder layout with `source="real"` in events and empty `defect_tag=""` in motion CSVs. Install the optional extra first: `uv sync --extra ingest`.

---

## Schemas

Pydantic models in `src/htdp/schemas/models.py`. JSON Schema exported to `docs/schemas/`.

**Changing a schema requires:**
1. Updating the Pydantic model.
2. Re-exporting JSON schemas (`uv run python -c "from pathlib import Path; from htdp.schemas.export import export_json_schemas; export_json_schemas(Path('docs/schemas'))"`).
3. Updating this document.
4. Updating or adding tests.

---

## Absent modalities in release manifests

The `absent_modalities` field in the release manifest (`manifest.json`) is now
**computed** from consent flags and on-disk file presence — no longer a fixed
`["eeg", "video"]`. A modality is recorded as absent if any session forbids it via its
consent (`distribute_raw_video`, `distribute_raw_eeg`) or if no files matching the
modality's glob patterns exist in any session. Motion data is never filtered and
never appears in this list.

---

## Canonical serialization rules (reproducibility)

- JSON: sorted keys, 2-space indent, UTF-8, LF.
- CSV: stable column order (as above), 6dp floats, UTF-8, LF.
- Parquet: reproducibility asserted at the logical manifest/checksum level, not raw bytes.
- Generated timestamps: seed-derived or excluded from hashed content.
- Tool versions: recorded in the manifest but excluded from the reproducibility checksum.

These rules ensure: same code + `uv.lock` + platform + seed + inputs → identical release-manifest checksums.

---

## Video stream (opaque MP4)

A raw session may contain a `video/` directory with one or more `.mp4` files.
Each video file is registered in `device_config.json` as a `StreamRef` with:

- `role`: `"video"`
- `fmt`: `"mp4"`
- `path`: `"video/<name>.mp4"` (relative to session root)
- `rate_hz`: the declared frame rate (fps) from the ingest sidecar

The `.mp4` file is stored **opaque**: it is copied as-is into the raw session
and never decoded, transcoded, or introspected by any pipeline stage. Frame
extraction and synchronization are deferred to v0.2+.

Video files are populated via `htdp ingest-video`, which registers a video
`StreamRef`, copies the file into the `video/` slot, and re-seals
`checksums.sha256`. At release time, consent filtering respects the
`distribute_raw_video` flag: sessions that disallow video distribution have
their video files excluded from the packaged release.

---

## Motion-BIDS export

The `htdp export-bids <raw_dir> <out_dir> [--force]` command reads a single raw session
and writes a minimal Motion-BIDS (BEP029) dataset tree. Key characteristics:

- Single raw session → separate BIDS directory; the raw session is never mutated.
- Irregular sampling is preserved via an explicit `timestamp_s` column and `n/a` fill
  (no resampling).
- The internal QC metadata column `defect_tag` is **not exported** — it is pipeline-internal,
  not motion data.
- BIDS version: **1.10.0**.
- Labels (`participant_id`, `protocol_id`, `device_config_id`) are sanitized to
  alphanumerics for BIDS entity compliance.
