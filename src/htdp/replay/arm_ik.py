from __future__ import annotations

from dataclasses import dataclass

from htdp.replay.ik import IkUnavailable
from htdp.replay.so_arm100 import EEF_BODY, SO_ARM100_XML


@dataclass
class ArmIkResult:
    joint_trajectory: list[list[float]]
    timestamps: list[float]
    targets: list[tuple[float, float, float]]
    errors: list[float]
    max_error: float


def solve_arm_ik(pose, *, ik_iters: int = 10) -> ArmIkResult:  # type: ignore[no-untyped-def]
    try:
        import mink  # type: ignore[import-not-found]
        import mujoco  # type: ignore[import-not-found]
        import numpy as np
        from mink.lie.se3 import SE3  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise IkUnavailable("install with: uv sync --extra replay") from exc

    model = mujoco.MjModel.from_xml_path(str(SO_ARM100_XML))
    data = mujoco.MjData(model)
    cfg = mink.Configuration(model)
    cfg.update(data.qpos)
    task = mink.FrameTask(
        frame_name=EEF_BODY, frame_type="body",
        position_cost=1.0, orientation_cost=0.0, lm_damping=1.0,
    )
    limits = [mink.ConfigurationLimit(model)]
    eid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, EEF_BODY)
    dt = model.opt.timestep

    traj: list[list[float]] = []
    ts: list[float] = []
    targets: list[tuple[float, float, float]] = []
    errors: list[float] = []
    max_error = 0.0
    for sample in pose:
        t, x, y, z = sample[0], sample[1], sample[2], sample[3]
        target = np.array([x, y, z])
        task.set_target(SE3.from_translation(target))
        for _ in range(ik_iters):
            vel = mink.solve_ik(cfg, [task], dt, "daqp", limits=limits)
            cfg.integrate_inplace(vel, dt)
        mujoco.mj_forward(model, cfg.data)
        traj.append([float(q) for q in cfg.data.qpos])
        err = float(np.linalg.norm(cfg.data.xpos[eid] - target))
        ts.append(float(t)); targets.append((float(x), float(y), float(z))); errors.append(err)
        max_error = max(max_error, err)
    return ArmIkResult(traj, ts, targets, errors, max_error)
