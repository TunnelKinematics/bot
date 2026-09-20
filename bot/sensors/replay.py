import json
from pathlib import Path

import cv2
import numpy as np

from .camera import StereoCamera
from .types import ImuSample, Intrinsics, StereoCalibration, StereoFrame


class ReplayCamera(StereoCamera):
    """Plays back a recording; get_stereo() raises EOFError at the end."""

    def __init__(self, path: str, start: int = 0, end: int | None = None):
        self.path = Path(path)
        self.start, self.end = start, end

    def open(self) -> None:
        c = json.loads((self.path / "calibration.json").read_text())

        def arr(k, default):
            return np.array(c[k]) if c.get(k) is not None else default

        self.calib = StereoCalibration(
            Intrinsics(**c["intrinsics"]),
            c["baseline"],
            arr("imu_to_left", None),
            arr("left_to_rig", np.eye(4)),
            c.get("serial", ""),
        )
        self.timestamps = np.loadtxt(
            self.path / "frames.csv", delimiter=",", skiprows=1, ndmin=2
        )[:, 1]
        self.imu = np.loadtxt(
            self.path / "imu.csv", delimiter=",", skiprows=1, ndmin=2
        )
        self.has_imu = len(self.imu) > 0
        self.i = self.start
        self.imu_i = 0

    def close(self) -> None: ...

    def calibration(self) -> StereoCalibration:
        return self.calib

    def get_stereo(self) -> StereoFrame:
        if self.i >= (self.end or len(self.timestamps)):
            raise EOFError("end of recording")

        def read(d):
            return cv2.imread(
                str(self.path / d / f"{self.i:06d}.png"), cv2.IMREAD_UNCHANGED
            )

        depth = None
        if (self.path / "depth").is_dir():
            depth = read("depth").astype(np.float32) / 1000
            depth[depth == 0] = np.nan
        sf = StereoFrame(
            read("left"), read("right"), depth, self.timestamps[self.i]
        )
        self.i += 1
        return sf

    def get_imu(self) -> list[ImuSample]:
        """Samples up to the last returned frame's timestamp."""
        until = self.timestamps[self.i - 1] if self.i > self.start else -np.inf
        j = self.imu_i + np.searchsorted(
            self.imu[self.imu_i :, 0], until, side="right"
        )
        rows, self.imu_i = self.imu[self.imu_i : j], j
        return [ImuSample(r[0], r[1:4], r[4:7]) for r in rows]
