# tests/learn/test_eval.py
import json

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("mujoco")
pytest.importorskip("mink")

from htdp.learn.dataset import generate_demos
from htdp.learn.eval import baseline_at, evaluate
from htdp.learn.train import train


def test_baseline_succeeds(tmp_path):
    rep = baseline_at([(0.50, -0.15), (0.48, -0.12)])
    assert rep["n"] == 2
    assert rep["success_rate"] == 1.0  # scripted teacher always places


def test_evaluate_end_to_end_smoke(tmp_path):
    ds = generate_demos(tmp_path / "demos", n_train=2, n_test=2, seed=0)
    ckpt = train(ds, tmp_path / "policy.pt", steps=50, batch=16, chunk=8, seed=0)
    positions = json.loads((ds / "meta" / "test_positions.json").read_text())
    rep = evaluate(ckpt, [tuple(p) for p in positions], out_path=tmp_path / "report.json")
    assert set(rep) == {"policy", "baseline"}
    assert "success_rate" in rep["policy"] and "success_rate" in rep["baseline"]
    assert (tmp_path / "report.json").exists()
