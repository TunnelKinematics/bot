import numpy as np
import pyzed.sl as sl

from .camera import StereoCamera
from .types import ImuSample, Intrinsics, StereoCalibration, StereoFrame


class ZedCamera(StereoCamera):
    def __init__(
        self,
        fps: int = 30,
        resolution: str = "HD720",
        warmup_s: float = 1.0,
        depth: bool = True,
        serial: int | str | None = None,
    ):
        """ZED stereo camera using the Python bindings shipped with ZED SDK."""
        self.fps = fps
        self.resolution = resolution
        self.depth = depth
        self.serial = serial
        self.warmup_s = warmup_s
        self.device: sl.Camera | None = None
        self._imu_samples: list[ImuSample] = []
        self._last_imu_timestamp = -1.0

    def open(self) -> None:
        init = sl.InitParameters()
        try:
            init.camera_resolution = getattr(sl.RESOLUTION, self.resolution)
        except AttributeError as exc:
            choices = [name for name in dir(sl.RESOLUTION) if name.isupper()]
            raise ValueError(
                f"unknown ZED resolution {self.resolution!r}; "
                f"choose one of {choices}"
            ) from exc
        init.camera_fps = self.fps
        init.depth_mode = (
            sl.DEPTH_MODE.PERFORMANCE
            if self.depth
            else sl.DEPTH_MODE.NONE
        )
        init.coordinate_units = sl.UNIT.METER
        init.coordinate_system = sl.COORDINATE_SYSTEM.IMAGE
        if self.serial is not None:
            init.set_from_serial_number(int(self.serial))

        self.device = sl.Camera()
        status = self.device.open(init)
        if status != sl.ERROR_CODE.SUCCESS:
            self.device.close()
            self.device = None
            raise RuntimeError(f"could not open ZED camera: {status}")

        self._imu_samples.clear()
        self._last_imu_timestamp = -1.0
        info = self.device.get_camera_information()
        self.has_imu = bool(
            info.sensors_configuration.accelerometer_parameters.is_available
        )
        self._left = sl.Mat()
        self._right = sl.Mat()
        self._depth = sl.Mat()
        self._runtime = sl.RuntimeParameters()
        self._calibration = self._read_calibration(info)

        # Let auto-exposure settle before returning the first usable frame.
        first_timestamp = self.get_stereo().timestamp
        while self.get_stereo().timestamp - first_timestamp < self.warmup_s:
            pass
        self._imu_samples.clear()

    def close(self) -> None:
        if self.device is not None:
            self.device.close()
            self.device = None

    def calibration(self) -> StereoCalibration:
        if self.device is None:
            raise RuntimeError("camera is not open")
        return self._calibration

    def _read_calibration(self, info) -> StereoCalibration:
        config = info.camera_configuration
        calib = config.calibration_parameters
        left = calib.left_cam
        right = calib.right_cam
        translation = calib.stereo_transform.get_translation().get()
        imu_to_left = (
            np.asarray(
                info.sensors_configuration.camera_imu_transform.m, dtype=float
            ).copy()
            if self.has_imu
            else None
        )
        size = (config.resolution.width, config.resolution.height)

        def intrinsics(camera) -> Intrinsics:
            return Intrinsics(
                camera.fx,
                camera.fy,
                camera.cx,
                camera.cy,
                *size,
            )

        return StereoCalibration(
            left_intrinsics=intrinsics(left),
            baseline=abs(float(translation[0])),
            imu_to_left=imu_to_left,
            serial=str(info.serial_number),
            imu_hz=(
                float(
                    info.sensors_configuration.accelerometer_parameters.sampling_rate
                )
                if self.has_imu
                else 0.0
            ),
            right_intrinsics=intrinsics(right),
        )

    def get_stereo(self) -> StereoFrame:
        if self.device is None:
            raise RuntimeError("camera is not open")
        status = self.device.grab(self._runtime)
        if status != sl.ERROR_CODE.SUCCESS:
            raise RuntimeError(f"could not grab ZED frame: {status}")
        self._retrieve_image(self._left, sl.VIEW.LEFT_GRAY)
        self._retrieve_image(self._right, sl.VIEW.RIGHT_GRAY)
        depth = None
        if self.depth:
            status = self.device.retrieve_measure(
                self._depth, sl.MEASURE.DEPTH
            )
            if status != sl.ERROR_CODE.SUCCESS:
                raise RuntimeError(f"could not retrieve ZED depth: {status}")
            depth = np.asarray(
                self._depth.get_data(), dtype=np.float32
            ).copy()
            depth[~np.isfinite(depth) | (depth <= 0)] = np.nan
        timestamp = self.device.get_timestamp(
            sl.TIME_REFERENCE.IMAGE
        ).get_seconds()
        self._read_imu_batch()
        return StereoFrame(
            np.asarray(self._left.get_data(), dtype=np.uint8).copy(),
            np.asarray(self._right.get_data(), dtype=np.uint8).copy(),
            depth,
            timestamp,
        )

    def get_imu(self) -> list[ImuSample]:
        if not self.has_imu:
            return []
        samples, self._imu_samples = self._imu_samples, []
        return samples

    def _retrieve_image(self, mat: sl.Mat, view) -> None:
        status = self.device.retrieve_image(mat, view)
        if status != sl.ERROR_CODE.SUCCESS:
            raise RuntimeError(f"could not retrieve ZED image: {status}")

    def _read_imu_batch(self) -> None:
        if not self.has_imu:
            return
        batch = []
        status = self.device.get_sensors_data_batch(batch)
        if status != sl.ERROR_CODE.SUCCESS:
            raise RuntimeError(f"could not retrieve ZED IMU batch: {status}")
        for data in batch:
            imu = data.get_imu_data()
            timestamp = imu.timestamp.get_seconds()
            if timestamp <= self._last_imu_timestamp:
                continue
            self._imu_samples.append(
                ImuSample(
                    timestamp,
                    np.asarray(
                        imu.get_linear_acceleration(), dtype=float
                    ).copy(),
                    np.deg2rad(
                        np.asarray(
                            imu.get_angular_velocity(), dtype=float
                        )
                    ),
                )
            )
            self._last_imu_timestamp = timestamp
