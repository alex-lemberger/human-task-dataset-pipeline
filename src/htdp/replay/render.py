from __future__ import annotations

from pathlib import Path

from htdp.replay.ik import IkUnavailable
from htdp.replay.scene import TASK_SCENE_XML


def render_episode(out_path: Path, *, fps: int = 30, every: int = 10, force: bool = False) -> Path:
    """Run the pick-and-place episode and write an MP4 of it.

    Captures one frame every ``every`` simulation steps via an offscreen MuJoCo renderer.
    Refuses to overwrite an existing file unless ``force``.
    """
    if out_path.exists() and not force:
        raise FileExistsError(f"refusing to overwrite {out_path} (use --force)")
    try:
        import imageio.v3 as iio  # type: ignore[import-not-found]
        import mujoco  # type: ignore[import-not-found]
        import numpy as np
    except ModuleNotFoundError as exc:
        raise IkUnavailable("install with: uv sync --extra replay") from exc

    from htdp.replay.episode import run_episode  # lazy import avoids a cycle

    model = mujoco.MjModel.from_xml_path(str(TASK_SCENE_XML))
    renderer = mujoco.Renderer(model, height=480, width=640)
    frames: list[np.ndarray] = []

    def on_step(data, step_index, grasp_active):  # type: ignore[no-untyped-def]
        if step_index % every == 0:
            renderer.update_scene(data)
            frames.append(renderer.render())

    run_episode(on_step=on_step)
    renderer.close()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    iio.imwrite(out_path, frames, fps=fps, codec="libx264")
    return out_path
