from __future__ import annotations

from dataclasses import dataclass

from htdp.replay.arm_ik import solve_arm_ik
from htdp.replay.ik import IkUnavailable
from htdp.replay.scene import OBJECT_BODY, OBJECT_FREEJOINT, TARGET_SITE, TASK_SCENE_XML
from htdp.replay.so_arm100 import EEF_BODY

# Vertical waypoint heights, in the SO-ARM100 reachable band (z in [0.04, 0.18]).
_Z_HI = 0.16
_Z_LO = 0.078  # cube centre sits at table_top(0.06) + cube_half(0.015) = 0.075


@dataclass
class EpisodeResult:
    object_start_xy: tuple[float, float]
    object_final_xy: tuple[float, float]
    target_xy: tuple[float, float]
    place_error: float
    frames_stepped: int
    qpos_trace: list[list[float]]


def _waypoints(model):  # type: ignore[no-untyped-def]
    # Cartesian path keyed off cube + target positions; (x, y, z, grasp_active).
    cube = model.body(OBJECT_BODY).pos
    tgt = model.site(TARGET_SITE).pos
    return [
        (cube[0], cube[1], _Z_HI, False),  # approach above cube
        (cube[0], cube[1], _Z_LO, False),  # descend to cube
        (cube[0], cube[1], _Z_LO, True),  # grasp (weld on)
        (cube[0], cube[1], _Z_HI, True),  # lift
        (tgt[0], tgt[1], _Z_HI, True),  # traverse to target
        (tgt[0], tgt[1], _Z_LO, True),  # descend to target
        (tgt[0], tgt[1], _Z_LO, False),  # release (weld off)
        (tgt[0], tgt[1], _Z_HI, False),  # retreat
    ]


def run_episode(*, interp: int = 25, settle: int = 6, seed: int = 0) -> EpisodeResult:
    try:
        import mujoco  # type: ignore[import-not-found]
        import numpy as np
    except ModuleNotFoundError as exc:
        raise IkUnavailable("install with: uv sync --extra replay") from exc

    model = mujoco.MjModel.from_xml_path(str(TASK_SCENE_XML))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)

    eef_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, EEF_BODY)
    cube_jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, OBJECT_FREEJOINT)
    cube_qadr = int(model.jnt_qposadr[cube_jid])
    cube_vadr = int(model.jnt_dofadr[cube_jid])

    n_arm = len(solve_arm_ik([(0.0, *model.body(OBJECT_BODY).pos, 1, 0, 0, 0)]).joint_trajectory[0])

    # Grasp is a kinematic attach: while held, the cube's free joint is slaved to the gripper
    # body at the relative offset captured the instant the grasp closes. Deterministic and
    # exact — a robust stand-in for a friction grasp for this demo (see design spec).
    grasp_offset = {"v": None}
    frames = 0

    def drive_to(x: float, y: float, z: float, grasp: bool) -> None:
        nonlocal frames
        sol = solve_arm_ik([(0.0, x, y, z, 1.0, 0.0, 0.0, 0.0)]).joint_trajectory[0]
        for _ in range(settle):
            data.qpos[:n_arm] = sol[:n_arm]
            data.qvel[:n_arm] = 0.0
            if grasp:
                if grasp_offset["v"] is None:
                    grasp_offset["v"] = data.body(OBJECT_BODY).xpos - data.xpos[eef_id]
                data.qpos[cube_qadr : cube_qadr + 3] = data.xpos[eef_id] + grasp_offset["v"]
                data.qpos[cube_qadr + 3 : cube_qadr + 7] = (1.0, 0.0, 0.0, 0.0)
                data.qvel[cube_vadr : cube_vadr + 6] = 0.0
            else:
                grasp_offset["v"] = None
            mujoco.mj_step(model, data)
            frames += 1

    start_xy = (float(data.body(OBJECT_BODY).xpos[0]), float(data.body(OBJECT_BODY).xpos[1]))
    waypoints = _waypoints(model)  # type: ignore[no-untyped-call]
    qtrace: list[list[float]] = []
    prev = waypoints[0][:3]
    for x, y, z, grasp in waypoints:
        # Interpolate from the previous keyframe so the arm (and the held cube) move in small
        # steps instead of teleporting between far IK solutions.
        for k in range(1, interp + 1):
            f = k / interp
            drive_to(
                prev[0] + (x - prev[0]) * f,
                prev[1] + (y - prev[1]) * f,
                prev[2] + (z - prev[2]) * f,
                grasp,
            )
        prev = (x, y, z)
        qtrace.append([float(q) for q in data.qpos])

    final_xy = (float(data.body(OBJECT_BODY).xpos[0]), float(data.body(OBJECT_BODY).xpos[1]))
    tgt = (float(model.site(TARGET_SITE).pos[0]), float(model.site(TARGET_SITE).pos[1]))
    place_error = float(np.hypot(final_xy[0] - tgt[0], final_xy[1] - tgt[1]))
    return EpisodeResult(start_xy, final_xy, tgt, place_error, frames, qtrace)
