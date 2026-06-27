import pytest

pytest.importorskip("mujoco")

import numpy as np

from htdp.learn.obs import ACTION_DIM, OBS_DIM, build_action, build_observation


def test_obs_and_action_shapes_and_target():
    import mujoco

    from htdp.replay.scene import TASK_SCENE_XML, TARGET_SITE

    m = mujoco.MjModel.from_xml_path(str(TASK_SCENE_XML))
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    gsid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SITE, "grasp_site")

    obs = build_observation(m, d, gsid)
    assert obs.shape == (OBS_DIM,)
    # last three entries are the fixed target xyz
    tgt = m.site(TARGET_SITE).pos
    assert np.allclose(obs[13:16], tgt)

    act_open = build_action(d, False)
    act_closed = build_action(d, True)
    assert act_open.shape == (ACTION_DIM,)
    assert act_open[7] == 0.0 and act_closed[7] == 1.0
    assert np.allclose(act_open[:7], d.qpos[:7])
