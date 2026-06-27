from __future__ import annotations

import numpy as np
import pytest

mujoco = pytest.importorskip("mink")  # IK backend
mujoco = pytest.importorskip("mujoco")

from htdp.replay.arm_ik import solve_arm_ik
from htdp.replay.franka import GRASP_SITE
from htdp.replay.physics_episode import track_joint_targets
from htdp.replay.scene import TASK_SCENE_PHYSICS_XML


def test_actuators_track_ik_target():
    model = mujoco.MjModel.from_xml_path(str(TASK_SCENE_PHYSICS_XML))
    data = mujoco.MjData(model)
    key = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "home")
    mujoco.mj_resetDataKeyframe(model, data, key)
    mujoco.mj_forward(model, data)
    grasp_sid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, GRASP_SITE)

    # IK a single reachable point above the table.
    target_xyz = (0.50, -0.15, 0.35)
    sol = solve_arm_ik([(0.0, *target_xyz, 1.0, 0.0, 0.0, 0.0)]).joint_trajectory
    track_joint_targets(model, data, sol, gripper_ctrl=255.0, settle=400)

    reached = data.site_xpos[grasp_sid]
    err = float(np.linalg.norm(np.array(target_xyz) - reached))
    assert err < 0.03, f"grasp site off target by {err:.3f} m"


def test_friction_grasp_lifts_cube():
    from htdp.replay.physics_episode import run_physics_episode

    res = run_physics_episode(cube_xy=(0.50, -0.15))
    assert res.lifted, "cube was not lifted by the friction grasp"
