from __future__ import annotations

import numpy as np

OBS_DIM = 16
ACTION_DIM = 8

# NOTE: the gripper finger width is deliberately NOT in the observation. The scripted teacher
# never actuates the fingers, so it is constant across every demo (std ~ 0) — a normalization
# landmine: any tiny mismatch at rollout produces an astronomically large normalized input that
# destroys the policy. A constant feature carries no information; it is dropped entirely.
OBS_NAMES = [
    *(f"q{i}" for i in range(7)),
    "eef_x", "eef_y", "eef_z",
    "cube_x", "cube_y", "cube_z",
    "tgt_x", "tgt_y", "tgt_z",
]
ACTION_NAMES = [*(f"q{i}_target" for i in range(7)), "gripper"]


def build_observation(model, data, grasp_sid: int) -> np.ndarray:  # type: ignore[no-untyped-def]
    """State observation, shape (16,). See OBS_NAMES for the layout."""
    eef = data.site_xpos[grasp_sid]
    cube = data.body("cube").xpos
    tgt = model.site("target").pos
    return np.concatenate(
        [
            data.qpos[:7],
            eef,
            cube,
            tgt,
        ]
    ).astype(np.float32)


def build_action(data, grasp_active: bool) -> np.ndarray:  # type: ignore[no-untyped-def]
    """Action, shape (8,): 7 joint position targets + gripper (1=close, 0=open)."""
    return np.concatenate(
        [data.qpos[:7], np.array([1.0 if grasp_active else 0.0])]
    ).astype(np.float32)
