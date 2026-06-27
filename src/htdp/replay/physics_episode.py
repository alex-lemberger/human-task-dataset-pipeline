from __future__ import annotations


def track_joint_targets(model, data, targets, gripper_ctrl, *, settle=20):  # type: ignore[no-untyped-def]
    """Drive the 7 arm position-servo actuators to each joint-target row under physics.

    ``targets`` is a sequence of 7-element joint-angle rows (e.g. ``solve_arm_ik(...).
    joint_trajectory``). For each row, ``data.ctrl[:7]`` is set to the row and ``data.ctrl[7]``
    to ``gripper_ctrl`` (0 = closed … 255 = open), then physics is advanced ``settle`` steps.
    No ``qpos`` overwrite — the actuators do the work.
    """
    import mujoco

    for row in targets:
        data.ctrl[:7] = row[:7]
        data.ctrl[7] = gripper_ctrl
        for _ in range(settle):
            mujoco.mj_step(model, data)
