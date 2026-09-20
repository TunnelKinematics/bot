from abc import ABC, abstractmethod

from .types import ImuSample, StereoCalibration, StereoFrame


class StereoCamera(ABC):
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

    def get_imu(self) -> list[ImuSample]:
        """All samples since the last call, oldest first."""
        return []

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *_):
        self.close()


def create_camera(backend: str, **kwargs) -> StereoCamera:
    if backend == "oak":
        from .oak import OakCamera

        return OakCamera(**kwargs)
    if backend == "replay":
        from .replay import ReplayCamera

        return ReplayCamera(**kwargs)
    raise ValueError(f"unknown camera backend: {backend}")
