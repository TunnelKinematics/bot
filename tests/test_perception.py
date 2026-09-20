import numpy as np
import pytest

from bot.common.types import Pose
from bot.sensors.types import Intrinsics, StereoCalibration, StereoFrame

CALIB = StereoCalibration(Intrinsics(400, 400, 320, 200, 640, 400), 0.075)
IDENTITY = Pose(np.zeros(3), np.array([0, 0, 0, 1.0]), 0.0)


def wall_frame(distance: float = 1.0, shift: int = 0) -> StereoFrame:
    """Textured wall `distance` ahead; `shift` scrolls the texture
    horizontally (right image = left shifted by disparity)."""
    v, u = np.mgrid[0:400, 0:640]
    tex = (127 + 100 * np.sin((u - shift) / 15) * np.cos(v / 20)).astype(
        np.uint8
    )
    disparity = int(round(CALIB.intrinsics.fx * CALIB.baseline / distance))
    return StereoFrame(
        tex,
        np.roll(tex, -disparity, 1),
        np.full((400, 640), distance, np.float32),
        0.0,
    )


def cell(grid, x, y):
    return grid.cells[
        int((y - grid.origin[1]) / grid.resolution),
        int((x - grid.origin[0]) / grid.resolution),
    ]


def test_nvblox_wall_ahead(tmp_path):
    pytest.importorskip("nvblox_torch")  # GPU only; runs on the Jetson / Modal
    from bot.perception.nvblox import NvbloxMapper

    m = NvbloxMapper([CALIB], grid_resolution=0.1)
    for _ in range(3):
        m.integrate([wall_frame()], IDENTITY)
    assert m.save_mesh(str(tmp_path / "mesh.ply")) > 1000
    g = m.occupancy()
    assert cell(g, 1.0, 0.0) == 100 and cell(g, 0.5, 0.0) == 0


def test_cuvslam_tracks_translation():
    pytest.importorskip("cuvslam")  # GPU only; runs on the Jetson / Modal
    from bot.perception.cuvslam import Cuvslam

    slam = Cuvslam([CALIB], loop_closure=False)
    for i in range(10):
        pose = slam.track(
            [wall_frame(shift=4 * i)], []
        )  # 4px/frame at fx=400, z=1m: camera moves 1cm/frame left (body +y)
    assert slam.tracked
    assert np.allclose(pose.position, [0, 0.09, 0], atol=0.02)
