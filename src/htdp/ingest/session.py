from __future__ import annotations
import json

from dataclasses import dataclass

from htdp.ingest.frame import IDENTITY, Quat, apply_transform
from htdp.ingest.mapping import IngestMap, parse_ingest_map
from htdp.schemas.models import Consent, DeviceConfig, Session

_MOTION_COLS = [
    "timestamp_s",
    "tracker_id",
    "x_m",
    "y_m",
    "z_m",
    "qw",
    "qx",
    "qy",
    "qz",
    "quality",
    "defect_tag",
]
_EVENT_COLS = [
    "timestamp_s",
    "event_id",
    "label",
    "phase",
    "source",
    "confidence",
    "notes",
]
_TRACKER_ORDER = ("right_wrist", "left_wrist", "torso", "object")


@dataclass
class ParsedSidecar:
    session: Session
    consent: Consent
    device_config: DeviceConfig
    ingest_map: IngestMap
    rotation: Quat


def _rotation_from_sidecar(sidecar: dict[str, object]) -> Quat:
    ft = sidecar.get("frame_transform")
    if not isinstance(ft, dict):
        return IDENTITY
    rot = ft.get("rotation")
    if rot is None:
        return IDENTITY
    w, x, y, z = (float(v) for v in rot)
    return (w, x, y, z)


def validate_sidecar(sidecar: dict[str, object]) -> ParsedSidecar:
    """Validate schema blocks + ingest_map before any XDF read or write (fail fast)."""
    session = Session.model_validate(sidecar["session"])
    consent = Consent.model_validate(sidecar["consent"])
    device_config = DeviceConfig.model_validate(sidecar["device_config"])
    ingest_map = parse_ingest_map(sidecar["ingest_map"])  # type: ignore[arg-type]
    return ParsedSidecar(
        session=session,
        consent=consent,
        device_config=device_config,
        ingest_map=ingest_map,
        rotation=_rotation_from_sidecar(sidecar),
    )


def compute_t0(motion_raw: dict[str, list[dict[str, object]]]) -> float:
    all_ts = [float(r["raw_ts"]) for rows in motion_raw.values() for r in rows]  # type: ignore[arg-type]
    if not all_ts:
        raise ValueError("no motion samples found")
    return min(all_ts)


def build_motion_rows(
    motion_raw: dict[str, list[dict[str, object]]],
    rotation: Quat,
    t0: float,
) -> dict[str, list[dict[str, object]]]:
    out: dict[str, list[dict[str, object]]] = {}
    for tracker, rows in motion_raw.items():
        built: list[dict[str, object]] = []
        for r in rows:
            pos = (
                float(r["x_m"]),  # type: ignore[arg-type]
                float(r["y_m"]),  # type: ignore[arg-type]
                float(r["z_m"]),  # type: ignore[arg-type]
            )
            quat = (
                float(r["qw"]),  # type: ignore[arg-type]
                float(r["qx"]),  # type: ignore[arg-type]
                float(r["qy"]),  # type: ignore[arg-type]
                float(r["qz"]),  # type: ignore[arg-type]
            )
            (px, py, pz), (qw, qx, qy, qz) = apply_transform(rotation, pos, quat)
            built.append(
                {
                    "timestamp_s": float(r["raw_ts"]) - t0,  # type: ignore[arg-type]
                    "tracker_id": r["tracker_id"],
                    "x_m": px,
                    "y_m": py,
                    "z_m": pz,
                    "qw": qw,
                    "qx": qx,
                    "qy": qy,
                    "qz": qz,
                    "quality": float(r["quality"]),  # type: ignore[arg-type]
                    "defect_tag": "",
                }
            )
        out[tracker] = built
    return out


def build_event_rows(
    stamps: list[float],
    payloads: list[str],
    t0: float,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for ts, payload in zip(stamps, payloads):
        p = json.loads(payload)
        rows.append(
            {
                "timestamp_s": float(ts) - t0,
                "event_id": int(p["event_id"]),
                "label": str(p["label"]),
                "phase": str(p["phase"]),
                "source": "real",
                "confidence": float(p["confidence"]),
                "notes": str(p["notes"]),
            }
        )
    return rows
