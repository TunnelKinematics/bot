from abc import ABC, abstractmethod

from ..imu.base import ImuSource
from ..imu.types import ImuSample
from .types import Frame, StereoCalibration, StereoFrame


class StereoCamera(ImuSource, ABC):
    has_imu: bool = False

    @abstractmethod
    def open(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def calibration(self) -> StereoCalibration: ...

    @abstractmethod
    def get_stereo(self) -> StereoFrame:
        """Blocks for the next frame."""

    @abstractmethod
    def get_rgb(self) -> Frame:
        """Blocks for the next frame."""

    def get_imu(self) -> list[ImuSample]:
        return []

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *_):
        self.close()
