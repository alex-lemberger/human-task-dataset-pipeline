import json
from pathlib import Path

from htdp.release.package import package_release
from htdp.schemas.enums import ReleaseProfile
from htdp.synth.generate import generate_session


def _raw_with_video(tmp_path: Path, seed: int, allow_video: bool) -> Path:
    generate_session(tmp_path / "raw", seed=seed)
    sid = f"synth-{seed:04d}"
    (tmp_path / "raw" / sid / "video" / "clip.mp4").write_bytes(b"\x00\x01\x02")
    consent = tmp_path / "raw" / sid / "consent.json"
    data = json.loads(consent.read_text(encoding="utf-8"))
    data["distribute_raw_video"] = allow_video
    consent.write_text(json.dumps(data), encoding="utf-8")
    return tmp_path / "raw"


def test_allowed_video_is_included(tmp_path: Path):
    raw = _raw_with_video(tmp_path, 1, allow_video=True)
    out = package_release(
        ["synth-0001"], "rel", ReleaseProfile.COMMERCIAL_DATASET, raw, tmp_path / "releases"
    )
    assert (out / "data/synth-0001/video/clip.mp4").exists()
    manifest = json.loads((out / "manifest.json").read_text())
    assert "video" not in manifest["absent_modalities"]


def test_forbidden_video_is_dropped_session_kept(tmp_path: Path):
    raw = _raw_with_video(tmp_path, 1, allow_video=False)
    out = package_release(
        ["synth-0001"], "rel", ReleaseProfile.COMMERCIAL_DATASET, raw, tmp_path / "releases"
    )
    assert not (out / "data/synth-0001/video/clip.mp4").exists()  # dropped
    assert (out / "data/synth-0001/session.json").exists()  # session kept
    assert (out / "data/synth-0001/streams/motion_right_wrist.csv").exists()  # motion intact
    manifest = json.loads((out / "manifest.json").read_text())
    assert "video" in manifest["absent_modalities"]


def test_release_level_union_drops_for_all_sessions(tmp_path: Path):
    generate_session(tmp_path / "raw", seed=1)
    generate_session(tmp_path / "raw", seed=2)
    for seed in (1, 2):
        sid = f"synth-{seed:04d}"
        (tmp_path / "raw" / sid / "video" / "clip.mp4").write_bytes(b"\x00")
    # session 1 allows video, session 2 forbids it
    for seed, allow in ((1, True), (2, False)):
        sid = f"synth-{seed:04d}"
        c = tmp_path / "raw" / sid / "consent.json"
        d = json.loads(c.read_text(encoding="utf-8"))
        d["distribute_raw_video"] = allow
        c.write_text(json.dumps(d), encoding="utf-8")
    out = package_release(
        ["synth-0001", "synth-0002"],
        "rel",
        ReleaseProfile.COMMERCIAL_DATASET,
        tmp_path / "raw",
        tmp_path / "releases",
    )
    assert not (out / "data/synth-0001/video/clip.mp4").exists()  # dropped for allowing session too
    assert not (out / "data/synth-0002/video/clip.mp4").exists()
    manifest = json.loads((out / "manifest.json").read_text())
    assert "video" in manifest["absent_modalities"]
