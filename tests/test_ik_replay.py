# tests/test_ik_replay.py
from pathlib import Path

import pytest

from htdp.release.package import package_release
from htdp.schemas.enums import ReleaseProfile
from htdp.synth.generate import generate_session

pytest.importorskip("mink")

from htdp.replay.ik import replay_release_ik  # noqa: E402


def _release(tmp_path: Path) -> Path:
    generate_session(tmp_path / "raw", seed=1)
    return package_release(
        ["synth-0001"],
        "rel",
        ReleaseProfile.COMMERCIAL_DATASET,
        tmp_path / "raw",
        tmp_path / "releases",
    )


def test_tracks_wrist_within_tolerance(tmp_path: Path):
    res = replay_release_ik(_release(tmp_path), max_steps=30)
    assert len(res.joint_trajectory) == 30
    assert all(len(row) == 5 for row in res.joint_trajectory)
    assert res.max_error < 0.05


def test_deterministic(tmp_path: Path):
    rel = _release(tmp_path)
    a = replay_release_ik(rel, max_steps=20)
    b = replay_release_ik(rel, max_steps=20)
    assert a.joint_trajectory == b.joint_trajectory
