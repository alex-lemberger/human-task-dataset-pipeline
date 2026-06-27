# src/htdp/learn/rollout.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch

from htdp.learn.obs import build_observation
from htdp.learn.policy import ACTConfig, ACTPolicy
from htdp.learn.train import Normalizer


@dataclass
class RolloutResult:
    success: bool
    place_error: float
    lifted: bool
    cube_final_xy: tuple[float, float]
    steps: int


def load_policy(ckpt_path: Path) -> tuple[ACTPolicy, Normalizer]:
    ckpt: dict[str, Any] = torch.load(Path(ckpt_path), weights_only=False)
    cfg = ACTConfig(**ckpt["cfg"])
    net = ACTPolicy(cfg)
    net.load_state_dict(ckpt["state_dict"])
    net.eval()
    return net, Normalizer(ckpt["stats"])


_APPROACH_Z = 0.35  # ready-pose height above the table (matches the teacher's _Z_HI)
_FINGER_OPEN = 0.04  # fingers held open the whole episode (grasp is the kinematic attach)


def rollout_policy(
    policy: ACTPolicy,
    normalizer: Normalizer,
    cube_xy: tuple[float, float],
    *,
    exec_horizon: int = 16,
    max_chunks: int = 60,
    grasp_thresh: float = 0.05,
    grasp_gripper: float = 0.4,
) -> RolloutResult:
    """Closed-loop KINEMATIC rollout. The policy's joint targets are applied directly to qpos
    (consistent with the kinematic teacher), re-planning every ``exec_horizon`` actions
    (receding horizon). Grasp is the M1 kinematic attach, gated on the policy's gripper command
    plus cube proximity. The arm resets to an in-distribution ready pose above the cube via IK.
    """
    import mujoco

    from htdp.replay.arm_ik import solve_arm_ik
    from htdp.replay.scene import OBJECT_FREEJOINT, TARGET_SITE, TASK_SCENE_XML

    model = mujoco.MjModel.from_xml_path(str(TASK_SCENE_XML))
    data = mujoco.MjData(model)
    grasp_sid: int = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, "grasp_site")
    cube_jid: int = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, OBJECT_FREEJOINT)
    cube_qadr: int = int(model.jnt_qposadr[cube_jid])
    tgt: np.ndarray = model.site(TARGET_SITE).pos

    # Reset to a ready pose above the cube (in-distribution start; the teacher's first frame is
    # also an above-cube IK pose). Fingers held open to match the demo distribution.
    ready = solve_arm_ik([(0.0, cube_xy[0], cube_xy[1], _APPROACH_Z, 1.0, 0.0, 0.0, 0.0)])
    data.qpos[:7] = ready.joint_trajectory[0][:7]
    data.qpos[7] = _FINGER_OPEN
    data.qpos[8] = _FINGER_OPEN
    data.qpos[cube_qadr : cube_qadr + 2] = cube_xy
    mujoco.mj_forward(model, data)
    start_z = float(data.body("cube").xpos[2])

    attached: dict[str, Any] = {"on": False, "offset": None}
    lifted = False
    steps = 0
    for _ in range(max_chunks):
        obs = build_observation(model, data, grasp_sid)
        obs_t = normalizer.normalize_obs(torch.as_tensor(obs))
        chunk = normalizer.denormalize_action(policy.act(obs_t)).detach().numpy()
        for action in chunk[:exec_horizon]:
            data.qpos[:7] = action[:7]
            data.qvel[:7] = 0.0
            data.qpos[7] = _FINGER_OPEN
            data.qpos[8] = _FINGER_OPEN
            gripper = float(action[7])
            mujoco.mj_forward(model, data)
            if gripper > grasp_gripper and not attached["on"]:
                gap: np.ndarray = data.body("cube").xpos - data.site_xpos[grasp_sid]
                if float(np.linalg.norm(gap)) < grasp_thresh:
                    attached["on"] = True
                    attached["offset"] = gap.copy()
            if gripper <= grasp_gripper:
                attached["on"] = False
            if attached["on"]:
                data.qpos[cube_qadr : cube_qadr + 3] = (
                    data.site_xpos[grasp_sid] + attached["offset"]
                )
                data.qpos[cube_qadr + 3 : cube_qadr + 7] = (1.0, 0.0, 0.0, 0.0)
            mujoco.mj_forward(model, data)
            steps += 1
            if float(data.body("cube").xpos[2]) > start_z + 0.05:
                lifted = True

    cube: np.ndarray = data.body("cube").xpos
    place_error = float(np.hypot(cube[0] - tgt[0], cube[1] - tgt[1]))
    success = bool(place_error < 0.03 and lifted)
    return RolloutResult(success, place_error, lifted, (float(cube[0]), float(cube[1])), steps)
