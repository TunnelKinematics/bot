import depthai as dai
import numpy as np

from ..imu.types import ImuSample
from .base import StereoCamera
from .types import Frame, Intrinsics, StereoCalibration, StereoFrame

MONO_RES = dai.MonoCameraProperties.SensorResolution.THE_400_P
RGB_RES = dai.ColorCameraProperties.SensorResolution.THE_1080_P
RGB_ISP_SCALE = {1080: (1, 1), 720: (2, 3), 360: (1, 3)}


class OakCamera(StereoCamera):
    def __init__(self, fps: int = 30, rgb_height: int = 720, imu_hz: int = 200):
        self.fps = fps
        self.rgb_scale = RGB_ISP_SCALE[rgb_height]
        self.imu_hz = imu_hz
        self.device: dai.Device | None = None

    def open(self) -> None:
        self.device = dai.Device()
        self.has_imu = self.device.getConnectedIMU() != "NONE"
        self.device.startPipeline(self._pipeline())
        q = lambda name: self.device.getOutputQueue(name, maxSize=1, blocking=False)
        self.q_left, self.q_right, self.q_depth, self.q_rgb = map(q, ("left", "right", "depth", "rgb"))
        self.q_imu = q("imu") if self.has_imu else None

    def close(self) -> None:
        if self.device:
            self.device.close()
            self.device = None

    def _pipeline(self) -> dai.Pipeline:
        p = dai.Pipeline()

        def mono(socket):
            cam = p.create(dai.node.MonoCamera)
            cam.setBoardSocket(socket)
            cam.setResolution(MONO_RES)
            cam.setFps(self.fps)
            return cam

        def out(name, src):
            x = p.create(dai.node.XLinkOut)
            x.setStreamName(name)
            src.link(x.input)

        stereo = p.create(dai.node.StereoDepth)
        stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.ROBOTICS)
        cfg = stereo.initialConfig.get()
        cfg.postProcessing.decimationFilter.decimationFactor = 1  # keep depth at mono res
        stereo.initialConfig.set(cfg)
        stereo.setLeftRightCheck(True)
        stereo.setDepthAlign(dai.StereoDepthProperties.DepthAlign.RECTIFIED_LEFT)
        mono(dai.CameraBoardSocket.CAM_B).out.link(stereo.left)
        mono(dai.CameraBoardSocket.CAM_C).out.link(stereo.right)
        out("left", stereo.rectifiedLeft)
        out("right", stereo.rectifiedRight)
        out("depth", stereo.depth)

        rgb = p.create(dai.node.ColorCamera)
        rgb.setBoardSocket(dai.CameraBoardSocket.CAM_A)
        rgb.setResolution(RGB_RES)
        rgb.setFps(self.fps)
        rgb.setIspScale(*self.rgb_scale)
        out("rgb", rgb.video)

        if self.has_imu:
            imu = p.create(dai.node.IMU)
            imu.enableIMUSensor([dai.IMUSensor.ACCELEROMETER_RAW, dai.IMUSensor.GYROSCOPE_RAW], self.imu_hz)
            imu.setBatchReportThreshold(1)
            imu.setMaxBatchReports(20)
            out("imu", imu.out)
        return p

    def calibration(self) -> StereoCalibration:
        calib = self.device.readCalibration()
        w, h = 640, 400
        # depthai rectifies both mono streams into the right camera's intrinsics
        K = calib.getCameraIntrinsics(dai.CameraBoardSocket.CAM_C, w, h)
        return StereoCalibration(
            Intrinsics(K[0][0], K[1][1], K[0][2], K[1][2], w, h),
            calib.getBaselineDistance() / 100,
        )

    def get_stereo(self) -> StereoFrame:
        left = self.q_left.get()
        depth = self.q_depth.get().getFrame().astype(np.float32) / 1000
        depth[depth == 0] = np.nan
        return StereoFrame(
            left.getCvFrame(),
            self.q_right.get().getCvFrame(),
            depth,
            left.getTimestamp().total_seconds(),
        )

    def get_rgb(self) -> Frame:
        f = self.q_rgb.get()
        return Frame(f.getCvFrame(), f.getTimestamp().total_seconds())

    def get_imu(self) -> list[ImuSample]:
        if not self.q_imu:
            return []
        samples = []
        while (data := self.q_imu.tryGet()) is not None:
            for p in data.packets:
                a, g = p.acceleroMeter, p.gyroscope
                samples.append(ImuSample(
                    a.getTimestamp().total_seconds(),
                    np.array([a.x, a.y, a.z]),
                    np.array([g.x, g.y, g.z]),
                ))
        return samples
