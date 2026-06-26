from __future__ import annotations

import numpy as np

OBS_DIM = 17
ACTION_DIM = 8

OBS_NAMES = [
    *(f"q{i}" for i in range(7)),
    "finger_width",
    "eef_x", "eef_y", "eef_z",
    "cube_x", "cube_y", "cube_z",
    "tgt_x", "tgt_y", "tgt_z",
]
ACTION_NAMES = [*(f"q{i}_target" for i in range(7)), "gripper"]


def build_observation(model, data, grasp_sid: int) -> np.ndarray:  # type: ignore[no-untyped-def]
    """State observation, shape (17,). See OBS_NAMES for the layout."""
    eef = data.site_xpos[grasp_sid]
    cube = data.body("cube").xpos
    tgt = model.site("target").pos
    return np.concatenate(
        [
            data.qpos[:7],
            data.qpos[7:8],  # finger_joint1 ~ half the gripper width
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
