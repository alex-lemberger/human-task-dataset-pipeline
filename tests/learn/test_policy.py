import pytest

torch = pytest.importorskip("torch")

from htdp.learn.policy import ACTConfig, ACTPolicy


def test_forward_and_act_shapes():
    cfg = ACTConfig()
    net = ACTPolicy(cfg)
    out = net(torch.zeros(4, cfg.obs_dim))
    assert out.shape == (4, cfg.chunk, cfg.action_dim)

    single = net.act(torch.zeros(cfg.obs_dim))
    assert single.shape == (cfg.chunk, cfg.action_dim)


def test_overfit_one_batch_loss_drops():
    torch.manual_seed(0)
    cfg = ACTConfig(chunk=4, hidden=64, layers=1)
    net = ACTPolicy(cfg)
    obs = torch.randn(8, cfg.obs_dim)
    target = torch.randn(8, cfg.chunk, cfg.action_dim)
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3)
    first = last = None
    for i in range(100):
        opt.zero_grad()
        loss = torch.nn.functional.l1_loss(net(obs), target)
        loss.backward()
        opt.step()
        if i == 0:
            first = loss.item()
        last = loss.item()
    assert last < first * 0.5
