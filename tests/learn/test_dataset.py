# tests/learn/test_dataset.py
import json

import pytest

pytest.importorskip("mujoco")
pytest.importorskip("mink")

from htdp.learn.dataset import generate_demos, sample_cube_positions


def test_sample_positions_deterministic_and_in_region():
    a = sample_cube_positions(5, seed=0)
    b = sample_cube_positions(5, seed=0)
    assert a == b
    for x, y in a:
        assert 0.45 <= x <= 0.55 and -0.20 <= y <= -0.10


def test_generate_demos_writes_lerobot_layout(tmp_path):
    out = generate_demos(tmp_path / "demos", n_train=2, n_test=1, seed=0)

    # parquet episodes exist for the 2 train demos
    eps = sorted((out / "data" / "chunk-000").glob("episode_*.parquet"))
    assert len(eps) == 2

    import polars as pl

    df = pl.read_parquet(eps[0])
    assert set(["observation.state", "action", "timestamp", "frame_index",
                "episode_index", "index"]).issubset(df.columns)
    assert len(df["observation.state"][0]) == 16
    assert len(df["action"][0]) == 8

    info = json.loads((out / "meta" / "info.json").read_text())
    assert info["fps"] == 25
    assert info["features"]["observation.state"]["shape"] == [16]

    stats = json.loads((out / "meta" / "stats.json").read_text())
    assert len(stats["observation.state"]["mean"]) == 16
    assert len(stats["action"]["mean"]) == 8

    test_pos = json.loads((out / "meta" / "test_positions.json").read_text())
    assert len(test_pos) == 1
