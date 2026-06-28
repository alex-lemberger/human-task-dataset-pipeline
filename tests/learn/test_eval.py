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


def test_policy_beats_zero_on_held_out(tmp_path):
    # Regression guard for the 0%->100% fix: a small policy must achieve nonzero
    # held-out success. Catches reverts of the obs-landmine / kinematic-exec /
    # receding-horizon fixes that silently zeroed success.
    import json

    from htdp.learn.rollout import load_policy, rollout_policy

    ds = generate_demos(tmp_path / "demos", n_train=30, n_test=6, seed=0)
    ckpt = train(ds, tmp_path / "policy.pt", steps=2500, batch=32, seed=0)
    net, norm = load_policy(ckpt)
    positions = [tuple(p) for p in json.loads((ds / "meta" / "test_positions.json").read_text())]
    results = [rollout_policy(net, norm, p) for p in positions]
    success_rate = sum(r.success for r in results) / len(results)
    assert success_rate > 0.0, f"policy learned nothing (success_rate={success_rate})"


def test_visuomotor_policy_beats_zero_on_held_out(tmp_path):
    """B3 capstone gate: a policy that sees ONLY the front image + proprio (no privileged cube or
    target xyz) must achieve nonzero held-out success under true physics. Proves the CNN localises
    the cube and goal from pixels and drives a friction grasp closed-loop. seed=0 measured 4/6."""
    import json

    from htdp.learn.rollout import load_visuomotor_policy, rollout_visuomotor_policy
    from htdp.learn.train import train_visuomotor

    ds = generate_demos(tmp_path / "demos", n_train=40, n_test=6, seed=0)
    ckpt = train_visuomotor(ds, tmp_path / "vm.pt", steps=6000, batch=32, seed=0)
    net, norm = load_visuomotor_policy(ckpt)
    positions = [tuple(p) for p in json.loads((ds / "meta" / "test_positions.json").read_text())]
    results = [rollout_visuomotor_policy(net, norm, p) for p in positions]
    success_rate = sum(r.success for r in results) / len(results)
    assert success_rate > 0.0, f"visuomotor policy learned nothing (success_rate={success_rate})"
