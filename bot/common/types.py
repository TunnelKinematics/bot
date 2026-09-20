from dataclasses import dataclass

import numpy as np
from scipy.spatial.transform import Rotation

# Body frame is REP-103 (x forward, y left, z up); the camera optical
# frame is x right, y down, z forward.
T_BODY_OPTICAL = np.array(
    [[0, 0, 1, 0], [-1, 0, 0, 0], [0, -1, 0, 0], [0, 0, 0, 1]], dtype=float
)


@dataclass(frozen=True)
class Pose:
    position: np.ndarray  # xyz meters
    orientation: np.ndarray  # quaternion xyzw
    timestamp: float

    @property
    def matrix(self) -> np.ndarray:
        T = np.eye(4)
        T[:3, :3] = Rotation.from_quat(self.orientation).as_matrix()
        T[:3, 3] = self.position
        return T

    @classmethod
    def from_matrix(cls, T: np.ndarray, timestamp: float) -> "Pose":
        return cls(
            T[:3, 3].copy(),
            Rotation.from_matrix(T[:3, :3]).as_quat(),
            timestamp,
        )
