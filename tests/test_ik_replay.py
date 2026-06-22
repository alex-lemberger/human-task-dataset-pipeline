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


def test_cli_replay_ik(tmp_path: Path):
    from typer.testing import CliRunner

    from htdp.cli import app

    rel = _release(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["replay-ik", str(rel), "--max-steps", "10"])
    assert result.exit_code == 0, result.output
    assert "max tracking error" in result.output


def test_result_carries_per_step_metadata(tmp_path: Path):
    res = replay_release_ik(_release(tmp_path), max_steps=10)
    n = len(res.joint_trajectory)
    assert n == 10
    assert len(res.timestamps) == n
    assert len(res.targets) == n
    assert len(res.errors) == n
    assert res.max_error == max(res.errors)
    assert all(len(t) == 3 for t in res.targets)


def test_cli_replay_ik_out(tmp_path: Path):
    from typer.testing import CliRunner

    from htdp.cli import app

    rel = _release(tmp_path)
    out = tmp_path / "traj.csv"
    runner = CliRunner()
    result = runner.invoke(app, ["replay-ik", str(rel), "--max-steps", "10", "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()
    assert "wrote" in result.output

    import csv

    rows = list(csv.reader(out.open(encoding="utf-8")))
    assert len(rows) == 11  # header + 10 steps
    assert [c for c in rows[0] if c.startswith("q")] == ["q0", "q1", "q2", "q3", "q4"]


def test_cli_replay_ik_out_refuses_overwrite(tmp_path: Path):
    from typer.testing import CliRunner

    from htdp.cli import app

    rel = _release(tmp_path)
    out = tmp_path / "traj.csv"
    out.write_text("OLD", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(app, ["replay-ik", str(rel), "--max-steps", "5", "--out", str(out)])
    assert result.exit_code == 1
    assert "error:" in result.output

    forced = runner.invoke(
        app, ["replay-ik", str(rel), "--max-steps", "5", "--out", str(out), "--force"]
    )
    assert forced.exit_code == 0, forced.output
    assert "OLD" not in out.read_text(encoding="utf-8")


def test_orientation_recorded_at_zero_cost(tmp_path: Path):
    rel = _release(tmp_path)
    res = replay_release_ik(rel, max_steps=10)
    assert len(res.target_orientations) == 10
    assert len(res.orientation_errors) == 10
    assert all(len(q) == 4 for q in res.target_orientations)
    res0 = replay_release_ik(rel, max_steps=10, orientation_cost=0.0)
    assert res.joint_trajectory == res0.joint_trajectory


def test_orientation_cost_runs_and_is_deterministic(tmp_path: Path):
    rel = _release(tmp_path)
    a = replay_release_ik(rel, max_steps=10, orientation_cost=1.0)
    b = replay_release_ik(rel, max_steps=10, orientation_cost=1.0)
    assert isinstance(a.max_orientation_error, float)
    assert a.max_orientation_error >= 0.0
    assert a.joint_trajectory == b.joint_trajectory
