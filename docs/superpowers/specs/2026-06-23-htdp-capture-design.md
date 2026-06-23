# htdp-capture — VIVE→LSL→XDF capture app (design)

**Date:** 2026-06-23
**Status:** Approved (brainstorm complete)
**Repo:** new separate repo `htdp-capture` (NOT a subdir of human-task-dataset-pipeline)

## Purpose

Upstream data source for the human-task-dataset-pipeline (htdp). Produces a
contract-conforming `.xdf` recording plus an `ingest.json` sidecar that
`htdp ingest` already consumes. Turns on real human-task data capture.

This spec covers the **hardware-free spine**: everything from a pose source
through LSL outlets, an in-house recorder, XDF + sidecar output, verified by a
real round-trip through `htdp ingest`. The OpenVR/SteamVR adapter and real frame
calibration are explicitly deferred to a later hardware milestone.

## The contract to hit (from htdp `src/htdp/ingest/mapping.py`)

The emitted `.xdf` must contain:
- ≥1 numeric **motion** LSL stream per tracker, channels in exact order:
  `x_m, y_m, z_m, qw, qx, qy, qz, quality`
- exactly **one** events/markers stream (string)
- optional **eeg** streams (OUT OF SCOPE for this spine)
- `tracker_id` ∈ `{right_wrist, left_wrist, torso, object}`

Plus a sidecar `ingest.json` with `ingest_map` (each stream → role / tracker /
channel-index map) and `frame_transform`. Shape mirrors htdp
`tests/_xdf_writer.py` + `build_sidecar`.

## Decisions (locked in brainstorm)

1. **Separate repo** — distinct dependency surface (pylsl/OpenVR vs polars/mujoco),
   distinct lifecycle (field tool vs data pipeline). Coupling stays at the
   artifact (the `.xdf` + sidecar), not the code.
2. **Own XDF writer + in-house pylsl inlet recorder** — pose source → real
   `pylsl` outlets → our recorder pulls inlets → our writer serializes `.xdf`.
   Full LSL contract exercised in-process, no external binary (no LabRecorder).
   Writer validated against `pyxdf` round-trip.
3. **`quality` = pose-validity flag in [0.0, 1.0]** — mock emits `1.0` (with
   injectable dropout → `0.0` for testing). OpenVR later maps `eTrackingResult`.
4. **`MarkerSource` interface + `ScriptedMarkerSource`** for the spine,
   free-string labels. htdp ingest treats events as opaque strings. Recommended
   (not enforced) vocab: reach/grasp/move/place/release/idle.
5. **`frame_transform`: identity default, data-declared in config.** Real
   calibration deferred. Sidecar auto-generated from config.
6. **Contract sync via vendored constants + round-trip conformance test.**
   Capture repo owns its constants; `htdp` is a **dev/test-only** dependency
   driving a real `htdp ingest` round-trip. The test IS the contract guard —
   contract drift goes red. No shared package (YAGNI), no htdp at runtime.

## Architecture & module layout

New repo `htdp-capture`, package `htdp_capture`:

```
htdp_capture/
  contract.py        # vendored constants: MOTION_CHANNELS order, TRACKER_IDS, sidecar key shape
  pose_source.py     # PoseSource ABC + Pose dataclass
  mock_pose.py       # MockPoseSource (synthetic poses, injectable dropout for quality)
  marker_source.py   # MarkerSource ABC
  scripted_marker.py # ScriptedMarkerSource (fixed (t,label) sequence)
  outlets.py         # builds LSL outlets in contract channel order (motion per tracker + 1 markers)
  recorder.py        # in-house pylsl inlet recorder → captured samples
  xdf_writer.py      # serialize captured streams → .xdf (validated vs pyxdf)
  sidecar.py         # generate ingest.json (ingest_map + frame_transform) from config
  config.py          # capture config: trackers+roles, frame_transform (identity default), marker script, durations
  app.py             # orchestrator: wire source→outlets→recorder→xdf+sidecar
  cli.py             # `htdp-capture record ...` entrypoint
```

**Data flow:** `config` → `app` starts motion outlets (from PoseSource) + a
markers outlet (from MarkerSource) → `recorder` resolves & pulls inlets → on
stop, `xdf_writer` writes `.xdf` and `sidecar` writes `ingest.json` → both
consumed by `htdp ingest`.

**Runtime deps:** `pylsl`, `numpy`, `pyxdf`.
**Dev/test deps:** `htdp` (round-trip conformance), `pytest`, `ruff`, `mypy`.

## Key interfaces

### Pose (dataclass)
- `t: float`
- `pos: tuple[float, float, float]`
- `quat: tuple[float, float, float, float]`  (wxyz)
- `quality: float`

### PoseSource (ABC)
```python
class PoseSource(ABC):
    @abstractmethod
    def trackers(self) -> list[str]: ...        # subset of TRACKER_IDS
    @abstractmethod
    def poll(self) -> dict[str, Pose]: ...        # one sample per tracker, current time
    def close(self) -> None: ...
```
`MockPoseSource(trackers, rate_hz, motion_fn=..., dropout_frames=set())` —
synthetic motion (mirrors htdp synth motion shape); `quality=0.0` on
`dropout_frames`, else `1.0`.

### MarkerSource (ABC)
`poll() -> list[tuple[float, str]]` (markers due since last poll).
`ScriptedMarkerSource(schedule: list[tuple[float, str]])` — fires labels at
offsets from start. Free-string labels.

### outlets.py
- Per tracker: one `StreamOutlet`, type `motion`, 8 float32 channels in
  `MOTION_CHANNELS` order. Channel labels set in outlet XML so the XDF carries
  them.
- One markers outlet: type `Markers`, 1 string channel, irregular rate.

### recorder.py
Resolves outlets by name, opens inlets, pulls timestamped samples into
per-stream buffers until stop (duration- or marker-driven).
**`dejitter` and clock-sync OFF** — mirrors htdp ingest's
`dejitter_timestamps=False, synchronize_clocks=False` (htdp slice-1 lesson:
default dejitter resampled timestamps and broke round-trip).

### sidecar.py
`build_sidecar(config) -> dict`: `ingest_map` entry per stream (role /
tracker_id / channel index map) + `frame_transform` (identity default). Shape
mirrors htdp `tests/_xdf_writer.py` + `build_sidecar`.

### xdf_writer.py
Narrowest viable XDF serialization for the contract: file header with `XDF:`
magic prefix (htdp slice-1 lesson — dropped prefix broke ingest), per-stream
`StreamHeader` (channel labels, type, nominal rate, channel format), interleaved
sample chunks (timestamps + values), `StreamFooter`. Motion = float32, markers =
string. **Validation gate:** every written file round-trips through
`pyxdf.load_xdf` in tests; values + timestamps + channel labels assert-equal to
input.

## Error handling

- **Config:** validate trackers ⊆ `TRACKER_IDS`, ≥1 motion tracker,
  `frame_transform` shape — fail fast with clear error.
- **Recorder:** timeout if an outlet never resolves (guards hangs).
- **Writer:** `--force` guard on existing output (mirrors htdp export pattern).
- **Empty capture** (no samples) → explicit error, not a silent empty file.

## Testing (TDD, layered for hardware-free CI)

1. **Unit (no LSL):** `MockPoseSource` determinism, `ScriptedMarkerSource`
   schedule, `sidecar` shape, `config` validation, `xdf_writer` ↔ `pyxdf`
   round-trip.
2. **Integration (real pylsl, in-process):** outlets → recorder → captured
   samples match source. LSL loopback needs `pylsl`/liblsl present — pin it;
   gate this layer with `importorskip` if absent (no false-green — htdp lesson).
3. **Contract conformance (the payoff):** full `app` run → `.xdf` + `ingest.json`
   → `htdp ingest` (dev-dep) → assert resulting raw session matches what mock
   emitted (poses, markers, quality, per-tracker roles). Contract guard.

## Out of scope (deferred to later hardware milestone)

- `OpenVRPoseSource` (SteamVR + base stations + paired trackers via OpenVR /
  triad_openvr)
- real frame-transform calibration routine
- LabRecorder `.xdf` compatibility
- `ManualMarkerSource` (operator keypress/hotkey)
- one real end-to-end hardware capture
- EEG streams

## Related

- htdp v0.2 shipped (consumes this app's output) — memory `htdp-v02-state`
- kickoff context — memory `vive-capture-kickoff`
- htdp slice-1 XDF lessons: `XDF:` magic prefix, dejitter/sync OFF
