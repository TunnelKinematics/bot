from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class StereoFrame:
    left: np.ndarray  # rectified gray uint8
    right: np.ndarray
    depth: (
        np.ndarray | None
    )  # float32 meters in left frame, NaN = invalid; None without depth
    timestamp: float  # seconds, device clock


@dataclass(frozen=True)
class ImuSample:
    timestamp: float  # seconds, device clock
    accel: np.ndarray  # m/s^2, xyz
    gyro: np.ndarray  # rad/s, xyz


@dataclass(frozen=True)
class Intrinsics:
    fx: float
    fy: float
    cx: float
    cy: float
    width: int
    height: int

    @property
    def K(self) -> np.ndarray:
        return np.array(
            [[self.fx, 0, self.cx], [0, self.fy, self.cy], [0, 0, 1]]
        )


@dataclass(frozen=True)
class StereoCalibration:
    """One rectified stereo pair. A multi-camera rig is a list of these;
    the first pair's left optical frame is the rig frame."""

    intrinsics: Intrinsics  # shared by both rectified views
    baseline: float  # meters, right camera is +x of left
    imu_to_left: np.ndarray | None = (
        None  # 4x4, IMU frame -> left optical frame; None without an IMU
    )
    left_to_rig: np.ndarray = field(
        default_factory=lambda: np.eye(4)
    )  # 4x4, left optical frame -> rig frame (identity for the first pair)
    serial: str = ""  # device id, to tell the pairs of a rig apart
