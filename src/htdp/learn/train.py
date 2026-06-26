# src/htdp/learn/train.py
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl
import torch
from torch import Tensor

from htdp.learn.policy import ACTConfig, ACTPolicy


def pick_device() -> str:
    return "mps" if torch.backends.mps.is_available() else "cpu"


class Normalizer:
    def __init__(self, stats: dict) -> None:
        self.obs_mean = np.array(stats["observation.state"]["mean"], dtype=np.float32)
        self.obs_std = np.array(stats["observation.state"]["std"], dtype=np.float32)
        self.act_mean = np.array(stats["action"]["mean"], dtype=np.float32)
        self.act_std = np.array(stats["action"]["std"], dtype=np.float32)

    def normalize_obs(self, x: Tensor) -> Tensor:
        m = torch.as_tensor(self.obs_mean, device=x.device)
        s = torch.as_tensor(self.obs_std, device=x.device)
        return (x - m) / s

    def normalize_action(self, x: Tensor) -> Tensor:
        m = torch.as_tensor(self.act_mean, device=x.device)
        s = torch.as_tensor(self.act_std, device=x.device)
        return (x - m) / s

    def denormalize_action(self, x: Tensor) -> Tensor:
        m = torch.as_tensor(self.act_mean, device=x.device)
        s = torch.as_tensor(self.act_std, device=x.device)
        return x * s + m


def _build_samples(dataset_dir: Path, chunk: int):  # type: ignore[no-untyped-def]
    obs_list, tgt_list = [], []
    for ep in sorted((dataset_dir / "data" / "chunk-000").glob("episode_*.parquet")):
        df = pl.read_parquet(ep)
        obs = np.array(df["observation.state"].to_list(), dtype=np.float32)
        act = np.array(df["action"].to_list(), dtype=np.float32)
        n = len(obs)
        for t in range(n):
            chunk_act = act[t : t + chunk]
            if len(chunk_act) < chunk:  # pad by repeating the last action
                pad = np.repeat(act[-1:], chunk - len(chunk_act), axis=0)
                chunk_act = np.concatenate([chunk_act, pad], axis=0)
            obs_list.append(obs[t])
            tgt_list.append(chunk_act)
    return np.array(obs_list), np.array(tgt_list)


def train(
    dataset_dir: Path,
    out_path: Path,
    *,
    steps: int = 3000,
    batch: int = 64,
    lr: float = 1e-4,
    chunk: int = 20,
    seed: int = 0,
) -> Path:
    torch.manual_seed(seed)
    dataset_dir = Path(dataset_dir)
    stats = json.loads((dataset_dir / "meta" / "stats.json").read_text())
    norm = Normalizer(stats)
    device = pick_device()

    obs_np, tgt_np = _build_samples(dataset_dir, chunk)
    obs = norm.normalize_obs(torch.as_tensor(obs_np)).to(device)
    tgt = norm.normalize_action(torch.as_tensor(tgt_np)).to(device)

    cfg = ACTConfig(chunk=chunk)
    net = ACTPolicy(cfg).to(device)
    opt = torch.optim.AdamW(net.parameters(), lr=lr)
    rng = np.random.default_rng(seed)
    net.train()
    for _ in range(steps):
        idx = rng.integers(0, len(obs), size=min(batch, len(obs)))
        bi = torch.as_tensor(idx, device=device)
        opt.zero_grad()
        loss = torch.nn.functional.l1_loss(net(obs[bi]), tgt[bi])
        loss.backward()
        opt.step()

    out_path = Path(out_path)
    torch.save(
        {"state_dict": net.cpu().state_dict(), "cfg": vars(cfg), "stats": stats},
        out_path,
    )
    return out_path
