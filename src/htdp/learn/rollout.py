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


def rollout_policy(
    policy: ACTPolicy,
    normalizer: Normalizer,
    cube_xy: tuple[float, float],
    *,
    settle: int = 6,
    max_chunks: int = 40,
    grasp_thresh: float = 0.03,
) -> RolloutResult:
    import mujoco

    from htdp.replay.franka import home_qpos
    from htdp.replay.scene import OBJECT_FREEJOINT, TARGET_SITE, TASK_SCENE_XML

    model = mujoco.MjModel.from_xml_path(str(TASK_SCENE_XML))
    data = mujoco.MjData(model)
    grasp_sid: int = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, "grasp_site")
    cube_jid: int = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, OBJECT_FREEJOINT)
    cube_qadr: int = int(model.jnt_qposadr[cube_jid])
    cube_vadr: int = int(model.jnt_dofadr[cube_jid])
    tgt: np.ndarray = model.site(TARGET_SITE).pos

    data.qpos[:7] = home_qpos()[:7]  # type: ignore[no-untyped-call]
    data.qpos[cube_qadr : cube_qadr + 2] = cube_xy
    mujoco.mj_forward(model, data)
    ctrl_lo: np.ndarray = model.actuator_ctrlrange[:7, 0]
    ctrl_hi: np.ndarray = model.actuator_ctrlrange[:7, 1]
    start_z = float(data.body("cube").xpos[2])

    attached: dict[str, Any] = {"on": False, "offset": None}
    lifted = False
    steps = 0
    for _ in range(max_chunks):
        obs = build_observation(model, data, grasp_sid)
        obs_t = normalizer.normalize_obs(torch.as_tensor(obs))
        chunk = normalizer.denormalize_action(policy.act(obs_t)).detach().numpy()
        for action in chunk:
            data.ctrl[:7] = np.clip(action[:7], ctrl_lo, ctrl_hi)
            gripper = float(action[7])
            data.ctrl[7] = 255.0 * (1.0 - min(max(gripper, 0.0), 1.0))
            for _ in range(settle):
                mujoco.mj_forward(model, data)
                if gripper > 0.5 and not attached["on"]:
                    gap: np.ndarray = data.body("cube").xpos - data.site_xpos[grasp_sid]
                    if float(np.linalg.norm(gap)) < grasp_thresh:
                        attached["on"] = True
                        attached["offset"] = gap.copy()
                if gripper <= 0.5:
                    attached["on"] = False
                if attached["on"]:
                    data.qpos[cube_qadr : cube_qadr + 3] = (
                        data.site_xpos[grasp_sid] + attached["offset"]
                    )
                    data.qpos[cube_qadr + 3 : cube_qadr + 7] = (1.0, 0.0, 0.0, 0.0)
                    data.qvel[cube_vadr : cube_vadr + 6] = 0.0
                mujoco.mj_step(model, data)
                steps += 1
                if float(data.body("cube").xpos[2]) > start_z + 0.05:
                    lifted = True

    cube: np.ndarray = data.body("cube").xpos
    place_error = float(np.hypot(cube[0] - tgt[0], cube[1] - tgt[1]))
    success = bool(place_error < 0.03 and lifted)
    return RolloutResult(success, place_error, lifted, (float(cube[0]), float(cube[1])), steps)
