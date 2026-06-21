from __future__ import annotations

from dataclasses import dataclass

CONTRACT_TRACKERS: tuple[str, ...] = ("right_wrist", "left_wrist", "torso", "object")
_MOTION_CHANNEL_KEYS: tuple[str, ...] = (
    "x_m",
    "y_m",
    "z_m",
    "qw",
    "qx",
    "qy",
    "qz",
    "quality",
)


class MappingError(Exception):
    """Raised when the ingest_map does not resolve against the contract or XDF."""


@dataclass
class MotionStreamMap:
    tracker_id: str
    channels: dict[str, int]


@dataclass
class IngestMap:
    motion: dict[str, MotionStreamMap]
    events_stream: str


def parse_ingest_map(raw: dict[str, object]) -> IngestMap:
    motion: dict[str, MotionStreamMap] = {}
    events_streams: list[str] = []
    for stream_name, entry in raw.items():
        if not isinstance(entry, dict):
            raise MappingError(f"ingest_map entry for '{stream_name}' must be an object")
        role = entry.get("role")
        if role == "events":
            events_streams.append(stream_name)
        elif role == "motion":
            tracker_id = entry.get("tracker_id")
            if tracker_id not in CONTRACT_TRACKERS:
                raise MappingError(
                    f"stream '{stream_name}' tracker_id '{tracker_id}' "
                    f"not in contract trackers {CONTRACT_TRACKERS}"
                )
            channels = entry.get("channels")
            if not isinstance(channels, dict):
                raise MappingError(f"stream '{stream_name}' missing 'channels' map")
            missing = [k for k in _MOTION_CHANNEL_KEYS if k not in channels]
            if missing:
                raise MappingError(
                    f"stream '{stream_name}' channels missing keys: {', '.join(missing)}"
                )
            motion[stream_name] = MotionStreamMap(
                tracker_id=str(tracker_id),
                channels={k: int(channels[k]) for k in _MOTION_CHANNEL_KEYS},
            )
        else:
            raise MappingError(f"stream '{stream_name}' has unknown role '{role}'")

    if len(events_streams) != 1:
        raise MappingError(
            f"ingest_map must declare exactly one 'events' stream, found {len(events_streams)}"
        )
    if not motion:
        raise MappingError("ingest_map must declare at least one 'motion' stream")
    return IngestMap(motion=motion, events_stream=events_streams[0])
