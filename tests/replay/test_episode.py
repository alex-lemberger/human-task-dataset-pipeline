import math

import pytest

pytest.importorskip("mujoco")
pytest.importorskip("mink")

from htdp.replay.episode import run_episode


def test_episode_places_object_near_target_deterministically():
    a = run_episode()
    b = run_episode()
    assert a.qpos_trace == b.qpos_trace  # deterministic
    assert a.place_error < 0.05  # object placed within 5 cm of target
    moved = math.dist(a.object_start_xy, a.object_final_xy)
    assert moved > 0.05  # object actually moved from its start toward the target
