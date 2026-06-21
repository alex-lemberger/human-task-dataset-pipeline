from __future__ import annotations

import shutil
from pathlib import Path

from htdp.export.labels import entity_stem, sanitize
from htdp.export.sidecars import (
    PARTICIPANTS_HEADER,
    dataset_description,
    motion_json,
    participants_rows,
    readme_text,
)
from htdp.export.tabular import (
    CHANNELS_HEADER,
    EVENTS_HEADER,
    channels_rows,
    dicts_to_tsv,
    events_rows,
    matrix_to_tsv,
    motion_wide,
)
from htdp.io.canonical import dump_json
from htdp.schemas.models import DeviceConfig, Session


class BidsExportError(RuntimeError):
    """Raised when a raw session cannot be exported to Motion-BIDS."""


def _read_csv(path: Path) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    header = lines[0].split(",")
    return [dict(zip(header, line.split(","))) for line in lines[1:] if line]


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def export_motion_bids(raw_dir: Path, out_dir: Path, force: bool = False) -> Path:
    session_path = raw_dir / "session.json"
    device_path = raw_dir / "device_config.json"
    if not session_path.exists() or not device_path.exists():
        raise BidsExportError(f"raw session missing metadata: {raw_dir}")

    session = Session.model_validate_json(session_path.read_text(encoding="utf-8"))
    device = DeviceConfig.model_validate_json(device_path.read_text(encoding="utf-8"))
    motion_streams = [s for s in device.streams if s.role == "motion"]
    if not motion_streams:
        raise BidsExportError(f"no motion streams in {raw_dir}")

    trackers = [s.name for s in motion_streams]
    fps = motion_streams[0].rate_hz or 100.0
    rows: list[dict[str, str]] = []
    for s in motion_streams:
        rows.extend(_read_csv(raw_dir / s.path))
    events_path = raw_dir / "streams/events.csv"
    events = _read_csv(events_path) if events_path.exists() else []

    sub = sanitize(session.participant_id)
    task = sanitize(session.protocol_id)
    tracksys = sanitize(device.device_config_id)
    stem = entity_stem(sub, task, tracksys)

    m_header, m_matrix = motion_wide(rows, trackers)
    motion_tsv = matrix_to_tsv(m_header, m_matrix)
    channels_tsv = dicts_to_tsv(CHANNELS_HEADER, channels_rows(trackers, fps))
    events_tsv = dicts_to_tsv(EVENTS_HEADER, events_rows(events))
    participants_tsv = dicts_to_tsv(PARTICIPANTS_HEADER, participants_rows(sub, "n/a"))
    desc = dataset_description(session.session_id)
    sidecar = motion_json(task, tracksys, trackers, fps)
    readme = readme_text(session.session_id)

    if out_dir.exists():
        if not force:
            raise BidsExportError(f"output already exists: {out_dir} (use force=True)")
        shutil.rmtree(out_dir)
    motion_dir = out_dir / f"sub-{sub}" / "motion"
    motion_dir.mkdir(parents=True)

    dump_json(desc, out_dir / "dataset_description.json")
    _write_text(out_dir / "README", readme)
    _write_text(out_dir / "participants.tsv", participants_tsv)
    _write_text(motion_dir / f"{stem}_motion.tsv", motion_tsv)
    dump_json(sidecar, motion_dir / f"{stem}_motion.json")
    _write_text(motion_dir / f"{stem}_channels.tsv", channels_tsv)
    _write_text(motion_dir / f"sub-{sub}_task-{task}_events.tsv", events_tsv)
    return out_dir
