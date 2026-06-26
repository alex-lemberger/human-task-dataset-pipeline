from __future__ import annotations
from pathlib import Path

SO_ARM100_XML = Path(__file__).parent / "assets" / "so_arm100" / "scene.xml"

# Filled from introspection of the vendored MuJoCo Menagerie model:
EEF_BODY = "Moving_Jaw"
ARM_JOINTS = ("Rotation", "Pitch", "Elbow", "Wrist_Pitch", "Wrist_Roll")
GRIPPER_JOINT = "Jaw"


def load_model():  # type: ignore[no-untyped-def]
    import mujoco  # lazy

    return mujoco.MjModel.from_xml_path(str(SO_ARM100_XML))
