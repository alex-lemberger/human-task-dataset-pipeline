from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import Tensor, nn

from htdp.learn.obs import ACTION_DIM, OBS_DIM


@dataclass
class ACTConfig:
    obs_dim: int = OBS_DIM
    action_dim: int = ACTION_DIM
    chunk: int = 20
    hidden: int = 256
    heads: int = 4
    layers: int = 2


class ACTPolicy(nn.Module):
    """Compact action-chunking transformer: obs -> chunk of actions (deterministic)."""

    def __init__(self, cfg: ACTConfig) -> None:
        super().__init__()
        self.cfg = cfg
        self.obs_embed = nn.Linear(cfg.obs_dim, cfg.hidden)
        self.queries = nn.Parameter(torch.randn(cfg.chunk, cfg.hidden))
        layer = nn.TransformerDecoderLayer(
            d_model=cfg.hidden, nhead=cfg.heads, dim_feedforward=cfg.hidden * 4,
            batch_first=True,
        )
        self.decoder = nn.TransformerDecoder(layer, num_layers=cfg.layers)
        self.head = nn.Linear(cfg.hidden, cfg.action_dim)

    def forward(self, obs: Tensor) -> Tensor:
        b = obs.shape[0]
        memory = self.obs_embed(obs).unsqueeze(1)  # (B, 1, H)
        tgt = self.queries.unsqueeze(0).expand(b, -1, -1)  # (B, chunk, H)
        dec = self.decoder(tgt, memory)  # (B, chunk, H)
        return self.head(dec)  # (B, chunk, action_dim)

    @torch.no_grad()
    def act(self, obs: Tensor) -> Tensor:
        self.eval()
        return self.forward(obs.unsqueeze(0)).squeeze(0)
