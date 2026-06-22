from __future__ import annotations

import shutil
from pathlib import Path

from rosbags.rosbag2 import Writer
from rosbags.rosbag2.enums import StoragePlugin
from rosbags.typesys import Stores, get_typestore
from rosbags.typesys.stores.ros2_humble import (
    builtin_interfaces__msg__Time as Time,
    geometry_msgs__msg__Point as Point,
    geometry_msgs__msg__Pose as Pose,
    geometry_msgs__msg__PoseStamped as PoseStamped,
    geometry_msgs__msg__Quaternion as Quaternion,
    std_msgs__msg__Header as Header,
    std_msgs__msg__String as StringMsg,
)

from htdp.export.labels import sanitize
from htdp.schemas.models import DeviceConfig, Session

_TYPESTORE = get_typestore(Stores.ROS2_HUMBLE)


class RosbagExportError(RuntimeError):
    """Raised when a release/session cannot be exported to rosbag2."""


def _read_csv(path: Path) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    header = lines[0].split(",")
    return [dict(zip(header, line.split(","))) for line in lines[1:] if line]


def _ns(timestamp_s: float) -> int:
    return int(round(timestamp_s * 1e9))


def _pose_stamped(row: dict[str, str], frame_id: str) -> PoseStamped:
    ns = _ns(float(row["timestamp_s"]))
    return PoseStamped(
        header=Header(
            stamp=Time(sec=ns // 1_000_000_000, nanosec=ns % 1_000_000_000),
            frame_id=frame_id,
        ),
        pose=Pose(
            position=Point(x=float(row["x_m"]), y=float(row["y_m"]), z=float(row["z_m"])),
            orientation=Quaternion(
                x=float(row["qx"]), y=float(row["qy"]), z=float(row["qz"]), w=float(row["qw"])
            ),
        ),
    )


def _write_session_bag(bag_dir: Path, raw_dir: Path) -> None:
    session_path = raw_dir / "session.json"
    device_path = raw_dir / "device_config.json"
    if not session_path.exists() or not device_path.exists():
        raise RosbagExportError(f"raw session missing metadata: {raw_dir}")

    Session.model_validate_json(session_path.read_text(encoding="utf-8"))
    device = DeviceConfig.model_validate_json(device_path.read_text(encoding="utf-8"))
    motion_streams = [s for s in device.streams if s.role == "motion"]
    if not motion_streams:
        raise RosbagExportError(f"no motion streams in {raw_dir}")
    event_streams = [s for s in device.streams if s.role == "events"]

    with Writer(bag_dir, version=9, storage_plugin=StoragePlugin.MCAP) as writer:
        for stream in motion_streams:
            topic = f"/motion/{sanitize(stream.name)}"
            conn = writer.add_connection(topic, PoseStamped.__msgtype__, typestore=_TYPESTORE)
            for row in _read_csv(raw_dir / stream.path):
                msg = _pose_stamped(row, stream.name)
                writer.write(
                    conn,
                    _ns(float(row["timestamp_s"])),
                    _TYPESTORE.serialize_cdr(msg, PoseStamped.__msgtype__),
                )
        for stream in event_streams:
            conn = writer.add_connection("/events", StringMsg.__msgtype__, typestore=_TYPESTORE)
            for row in _read_csv(raw_dir / stream.path):
                event_msg = StringMsg(data=row["label"])
                writer.write(
                    conn,
                    _ns(float(row["timestamp_s"])),
                    _TYPESTORE.serialize_cdr(event_msg, StringMsg.__msgtype__),
                )


def export_release_rosbag(release_dir: Path, out_dir: Path, force: bool = False) -> Path:
    data_dir = release_dir / "data"
    if not data_dir.is_dir():
        raise RosbagExportError(f"release has no data/ directory: {release_dir}")
    session_dirs = sorted(p for p in data_dir.iterdir() if p.is_dir())
    if not session_dirs:
        raise RosbagExportError(f"release has no sessions: {release_dir}")

    if out_dir.exists():
        if not force:
            raise RosbagExportError(f"output already exists: {out_dir} (use force=True)")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    for sd in session_dirs:
        session = Session.model_validate_json((sd / "session.json").read_text(encoding="utf-8"))
        _write_session_bag(out_dir / sanitize(session.session_id), sd)
    return out_dir
