import pytest

pytest.importorskip("mujoco")

from htdp.replay.so_arm100 import (
    SO_ARM100_XML,
    EEF_BODY,
    ARM_JOINTS,
    GRIPPER_JOINT,
    load_model,
)


def test_model_loads_and_names_exist():
    import mujoco

    assert SO_ARM100_XML.exists()
    m = load_model()

    def has(objtype, name):
        return mujoco.mj_name2id(m, objtype, name) != -1

    assert has(mujoco.mjtObj.mjOBJ_BODY, EEF_BODY)
    for j in ARM_JOINTS:
        assert has(mujoco.mjtObj.mjOBJ_JOINT, j), j
    assert has(mujoco.mjtObj.mjOBJ_JOINT, GRIPPER_JOINT)
    assert len(ARM_JOINTS) == 5
