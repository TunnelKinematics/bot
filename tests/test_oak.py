import numpy as np


def test_calibration(oak):
    c = oak.calibration()
    assert 0.05 < c.baseline < 0.2
    assert c.intrinsics.fx > 0 and c.intrinsics.K.shape == (3, 3)


def test_stereo(oak):
    a, b = oak.get_stereo(), oak.get_stereo()
    assert a.left.shape == a.right.shape == a.depth.shape
    assert a.left.dtype == np.uint8 and a.depth.dtype == np.float32
    assert (a.left.shape[1], a.left.shape[0]) == (
        oak.calibration().intrinsics.width,
        oak.calibration().intrinsics.height,
    )
    assert np.nanmin(a.depth) > 0
    assert b.timestamp > a.timestamp


def test_imu(oak):
    if not oak.has_imu:
        assert oak.get_imu() == []
        return
    oak.get_stereo()  # let samples accumulate
    samples = oak.get_imu()
    assert samples
    assert 5 < np.linalg.norm(samples[-1].accel) < 15  # roughly 1g at rest
