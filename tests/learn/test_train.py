import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("mujoco")
pytest.importorskip("mink")

from htdp.learn.dataset import generate_demos
from htdp.learn.train import train


def test_train_writes_checkpoint(tmp_path):
    ds = generate_demos(tmp_path / "demos", n_train=2, n_test=1, seed=0)
    ckpt_path = train(ds, tmp_path / "policy.pt", steps=50, batch=16, chunk=8, seed=0)
    assert ckpt_path.exists()
    ckpt = torch.load(ckpt_path, weights_only=False)
    assert "state_dict" in ckpt and "cfg" in ckpt and "stats" in ckpt
