from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from htdp.replay.player import load_release_motion

_ARM_XML = Path(__file__).parent / "assets" / "arm.xml"


class IkUnavailable(RuntimeError):
    """Raised when mink/daqp/mujoco are not installed."""


@dataclass
class IkResult:
    joint_trajectory: list[list[float]]
    max_error: float


def replay_release_ik(release_dir: Path, max_steps: int = 50, ik_iters: int = 10) -> IkResult:
    try:
        import mink  # type: ignore[import-not-found]
        import mujoco  # type: ignore[import-not-found]
        import numpy as np
        from mink.lie.se3 import SE3  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise IkUnavailable("install with: uv sync --extra replay") from exc

    wrist = load_release_motion(release_dir)["right_wrist"]
    model = mujoco.MjModel.from_xml_path(str(_ARM_XML))
    data = mujoco.MjData(model)
    cfg = mink.Configuration(model)
    cfg.update(data.qpos)
    task = mink.FrameTask(
        frame_name="eef",
        frame_type="body",
        position_cost=1.0,
        orientation_cost=0.0,
        lm_damping=1.0,
    )
    limits = [mink.ConfigurationLimit(model)]
    eid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "eef")
    dt = model.opt.timestep

    n = min(max_steps, len(wrist))
    trajectory: list[list[float]] = []
    max_error = 0.0
    for i in range(n):
        _, x, y, z = wrist[i]
        target = np.array([x, y, z])
        task.set_target(SE3.from_translation(target))
        for _ in range(ik_iters):
            vel = mink.solve_ik(cfg, [task], dt, "daqp", limits=limits)
            cfg.integrate_inplace(vel, dt)
        mujoco.mj_forward(model, cfg.data)
        trajectory.append([float(q) for q in cfg.data.qpos])
        err = float(np.linalg.norm(cfg.data.xpos[eid] - target))
        max_error = max(max_error, err)
    return IkResult(joint_trajectory=trajectory, max_error=max_error)
