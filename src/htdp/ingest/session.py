from __future__ import annotations

from dataclasses import dataclass

from htdp.ingest.frame import IDENTITY, Quat
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
