# src/htdp/learn/eval.py
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from htdp.learn.rollout import load_policy, rollout_policy


def baseline_at(positions: list[tuple[float, float]]) -> dict[str, float | int]:
    from htdp.replay.episode import run_episode

    errs: list[float] = []
    succ = 0
    for cube_xy in positions:
        r = run_episode(cube_xy=tuple(cube_xy))
        errs.append(r.place_error)
        succ += int(r.place_error < 0.03)
    n = len(positions)
    return {
        "success_rate": succ / n if n else 0.0,
        "mean_place_error": float(np.mean(errs)) if errs else 0.0,
        "n": n,
    }


def _policy_at(
    ckpt_path: Path, positions: list[tuple[float, float]]
) -> dict[str, float | int]:
    net, norm = load_policy(ckpt_path)
    errs: list[float] = []
    succ = 0
    for cube_xy in positions:
        r = rollout_policy(net, norm, cube_xy)
        errs.append(r.place_error)
        succ += int(r.success)
    n = len(positions)
    return {
        "success_rate": succ / n if n else 0.0,
        "mean_place_error": float(np.mean(errs)) if errs else 0.0,
        "n": n,
    }


def evaluate(
    ckpt_path: Path,
    positions: list[tuple[float, float]],
    *,
    out_path: Path | None = None,
) -> dict[str, dict[str, float | int]]:
    report: dict[str, dict[str, float | int]] = {
        "policy": _policy_at(ckpt_path, positions),
        "baseline": baseline_at(positions),
    }
    if out_path is not None:
        Path(out_path).write_text(json.dumps(report, indent=2))
    return report
