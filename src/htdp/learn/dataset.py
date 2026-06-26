# src/htdp/learn/dataset.py
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl

from htdp.learn.obs import (
    ACTION_DIM,
    ACTION_NAMES,
    OBS_DIM,
    OBS_NAMES,
    build_action,
    build_observation,
)

CUBE_REGION = ((0.45, 0.55), (-0.20, -0.10))  # ((x_lo, x_hi), (y_lo, y_hi))
_SETTLE = 6
_TASK = "pick the cube and place it on the target"


def sample_cube_positions(n: int, seed: int) -> list[tuple[float, float]]:
    rng = np.random.default_rng(seed)
    (xlo, xhi), (ylo, yhi) = CUBE_REGION
    xs = rng.uniform(xlo, xhi, n)
    ys = rng.uniform(ylo, yhi, n)
    return [(float(x), float(y)) for x, y in zip(xs, ys)]


def _record_episode(cube_xy, ep_index, index_start, fps):  # type: ignore[no-untyped-def]
    """Run the scripted teacher once; return a list of row dicts, one per waypoint step."""
    import mujoco

    from htdp.replay.episode import run_episode
    from htdp.replay.scene import TASK_SCENE_XML

    model = mujoco.MjModel.from_xml_path(str(TASK_SCENE_XML))
    grasp_sid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, "grasp_site")

    rows: list[dict] = []

    def on_step(data, frame, grasp):  # type: ignore[no-untyped-def]
        if frame % _SETTLE != _SETTLE - 1:
            return
        fi = len(rows)
        rows.append(
            {
                "observation.state": build_observation(model, data, grasp_sid).tolist(),
                "action": build_action(data, grasp).tolist(),
                "timestamp": fi / fps,
                "frame_index": fi,
                "episode_index": ep_index,
                "index": index_start + fi,
            }
        )

    # Re-run with the SAME model instance so site ids match: run_episode builds its own
    # model internally, but ids for the shared scene file are identical, so reuse is safe.
    run_episode(cube_xy=cube_xy, on_step=on_step)
    return rows


def _feature_stats(values: np.ndarray) -> dict:
    return {
        "mean": values.mean(0).tolist(),
        "std": (values.std(0) + 1e-6).tolist(),
        "min": values.min(0).tolist(),
        "max": values.max(0).tolist(),
    }


def generate_demos(
    out_dir: Path,
    *,
    n_train: int = 100,
    n_test: int = 25,
    seed: int = 0,
    fps: int = 25,
) -> Path:
    out_dir = Path(out_dir)
    data_dir = out_dir / "data" / "chunk-000"
    meta_dir = out_dir / "meta"
    data_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    train_pos = sample_cube_positions(n_train, seed)
    test_pos = sample_cube_positions(n_test, seed + 1000)

    episodes_meta = []
    all_obs: list[list[float]] = []
    all_act: list[list[float]] = []
    index = 0
    for ep, cube_xy in enumerate(train_pos):
        rows = _record_episode(cube_xy, ep, index, fps)
        index += len(rows)
        pl.DataFrame(rows).write_parquet(data_dir / f"episode_{ep:06d}.parquet")
        episodes_meta.append({"episode_index": ep, "length": len(rows), "task": _TASK})
        all_obs.extend(r["observation.state"] for r in rows)
        all_act.extend(r["action"] for r in rows)

    info = {
        "codebase_version": "v2.0",
        "fps": fps,
        "robot_type": "franka_panda",
        "total_episodes": n_train,
        "total_frames": index,
        "features": {
            "observation.state": {"dtype": "float32", "shape": [OBS_DIM], "names": OBS_NAMES},
            "action": {"dtype": "float32", "shape": [ACTION_DIM], "names": ACTION_NAMES},
        },
    }
    (meta_dir / "info.json").write_text(json.dumps(info, indent=2))
    with (meta_dir / "episodes.jsonl").open("w") as fh:
        for em in episodes_meta:
            fh.write(json.dumps(em) + "\n")
    stats = {
        "observation.state": _feature_stats(np.array(all_obs, dtype=np.float32)),
        "action": _feature_stats(np.array(all_act, dtype=np.float32)),
    }
    (meta_dir / "stats.json").write_text(json.dumps(stats, indent=2))
    (meta_dir / "test_positions.json").write_text(json.dumps(test_pos))
    return out_dir
