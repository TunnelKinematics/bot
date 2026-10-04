import numpy as np


def test_calibration(zed):
    c = zed.calibration()
    assert 0.05 < c.baseline < 0.2
    assert c.left_intrinsics.fx > 0
    assert c.left_intrinsics.K.shape == (3, 3)
    assert c.right_intrinsics.fx > 0
    if zed.has_imu:
        assert c.imu_to_left.shape == (4, 4)
        assert c.imu_hz > 0


def test_stereo(zed):
    a, b = zed.get_stereo(), zed.get_stereo()
    assert a.left.shape == a.right.shape == a.depth.shape
    assert a.left.dtype == np.uint8 and a.depth.dtype == np.float32
    assert (a.left.shape[1], a.left.shape[0]) == (
        zed.calibration().left_intrinsics.width,
        zed.calibration().left_intrinsics.height,
    )
    assert np.nanmin(a.depth) > 0
    assert b.timestamp > a.timestamp


def test_imu(zed):
    if not zed.has_imu:
        assert zed.get_imu() == []
        return
    zed.get_stereo()  # let samples accumulate
    samples = zed.get_imu()
    assert samples
    assert 5 < np.linalg.norm(samples[-1].accel) < 15  # roughly 1g at rest
