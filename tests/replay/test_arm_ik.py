import pytest

pytest.importorskip("mujoco")
pytest.importorskip("mink")

from htdp.replay.arm_ik import solve_arm_ik


def _line(n=20):
    # a short reachable Cartesian path in the SO-ARM100 workspace (metres).
    # The arm reaches out along -y (EEF home ~ (0, -0.41, 0.12)), so targets sit
    # near y=-0.30 with small x and z in [0.12, 0.18]. tuple = (t, x, y, z, qw,qx,qy,qz).
    return [
        (0.04 * i, -0.05 + 0.006 * i, -0.30, 0.12 + 0.003 * i, 1.0, 0.0, 0.0, 0.0) for i in range(n)
    ]


def test_arm_ik_tracks_and_is_deterministic():
    a = solve_arm_ik(_line())
    b = solve_arm_ik(_line())
    assert a.max_error < 0.03
    assert a.joint_trajectory == b.joint_trajectory
    assert len(a.joint_trajectory) == 20
