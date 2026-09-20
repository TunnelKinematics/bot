from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ImuSample:
    timestamp: float  # seconds, device clock
    accel: np.ndarray  # m/s^2, xyz
    gyro: np.ndarray  # rad/s, xyz
