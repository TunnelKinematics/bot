from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Frame:
    image: np.ndarray  # BGR uint8
    timestamp: float


@dataclass(frozen=True)
class StereoFrame:
    left: np.ndarray  # rectified gray uint8
    right: np.ndarray
    depth: np.ndarray  # float32 meters in left frame, NaN = invalid
    timestamp: float


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
        return np.array([[self.fx, 0, self.cx], [0, self.fy, self.cy], [0, 0, 1]])


@dataclass(frozen=True)
class StereoCalibration:
    intrinsics: Intrinsics  # shared by both rectified views
    baseline: float  # meters
