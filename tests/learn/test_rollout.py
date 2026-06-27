# tests/learn/test_rollout.py
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("mujoco")
pytest.importorskip("mink")

from htdp.learn.policy import ACTConfig, ACTPolicy
from htdp.learn.rollout import RolloutResult, rollout_policy
from htdp.learn.train import Normalizer


def _dummy_norm():
    stats = {
        "observation.state": {"mean": [0.0] * 16, "std": [1.0] * 16,
                              "min": [0.0] * 16, "max": [1.0] * 16},
        "action": {"mean": [0.0] * 8, "std": [1.0] * 8,
                   "min": [0.0] * 8, "max": [1.0] * 8},
    }
    return Normalizer(stats)


def test_rollout_untrained_policy_runs_without_crashing():
    torch.manual_seed(0)
    net = ACTPolicy(ACTConfig(chunk=8))
    res = rollout_policy(net, _dummy_norm(), (0.50, -0.15), max_chunks=5)
    assert isinstance(res, RolloutResult)
    assert isinstance(res.success, bool)
    assert res.steps > 0


def test_rollout_is_deterministic():
    torch.manual_seed(0)
    net = ACTPolicy(ACTConfig(chunk=8))
    a = rollout_policy(net, _dummy_norm(), (0.50, -0.15), max_chunks=5)
    b = rollout_policy(net, _dummy_norm(), (0.50, -0.15), max_chunks=5)
    assert a.cube_final_xy == b.cube_final_xy
