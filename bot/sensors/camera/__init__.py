from .base import StereoCamera
from .types import Frame, Intrinsics, StereoCalibration, StereoFrame

__all__ = ["StereoCamera", "Frame", "Intrinsics", "StereoCalibration", "StereoFrame", "create_camera"]


def create_camera(backend: str, **kwargs) -> StereoCamera:
    if backend == "oak":
        from .oak import OakCamera
        return OakCamera(**kwargs)
    raise ValueError(f"unknown camera backend: {backend}")
