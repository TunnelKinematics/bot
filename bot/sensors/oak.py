import depthai as dai
import numpy as np

from .camera import StereoCamera
from .types import ImuSample, Intrinsics, StereoCalibration, StereoFrame

MONO_RES = dai.MonoCameraProperties.SensorResolution.THE_400_P
# BMI270 -> left optical frame on the OAK-D Lite: a 180 deg turn about x.
# Verified against gravity in several orientations; the EEPROM's
# getImuToCameraExtrinsics() rotation is wrong for this board (swaps x/y).
R_LEFT_IMU = np.diag([1.0, -1.0, -1.0])


class OakCamera(StereoCamera):
    def __init__(
        self,
        fps: int = 30,
        imu_hz: int = 200,
        warmup_s: float = 1.0,
        depth: bool = True,
        serial: str | None = None,
    ):
        """depth=False disables onboard stereo depth (left/right only);
        serial picks a device when several are connected."""
        self.fps = fps
        self.depth = depth
        self.serial = serial
        self.warmup_s = warmup_s
        self.imu_hz = imu_hz
        self.device: dai.Device | None = None

    def open(self) -> None:
        self.device = (
            dai.Device(dai.DeviceInfo(self.serial))
            if self.serial
            else dai.Device()
        )
        self.has_imu = self.device.getConnectedIMU() != "NONE"
        self.device.startPipeline(self._pipeline())

        def q(name):
            return self.device.getOutputQueue(name, maxSize=1, blocking=False)

        self.q_left, self.q_right = q("left"), q("right")
        self.q_depth = q("depth") if self.depth else None
        # IMU packets arrive at imu_hz; a maxSize=1 queue would keep only
        # the latest one per frame
        self.q_imu = (
            self.device.getOutputQueue(
                "imu", maxSize=2 * self.imu_hz, blocking=False
            )
            if self.has_imu
            else None
        )
        # Auto-exposure takes ~1 s to settle; frames before that are blown
        # out with almost no valid depth.
        t0 = self.get_stereo().timestamp
        while self.get_stereo().timestamp - t0 < self.warmup_s:
            pass

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
        stereo.setDefaultProfilePreset(
            dai.node.StereoDepth.PresetMode.ROBOTICS
        )
        cfg = stereo.initialConfig.get()
        cfg.postProcessing.decimationFilter.decimationFactor = (
            1  # keep depth at mono res
        )
        # hole-filling; at full res it halves the OAK-D Lite to 15 fps
        cfg.postProcessing.spatialFilter.enable = False
        stereo.initialConfig.set(cfg)
        stereo.setLeftRightCheck(True)
        stereo.setDepthAlign(
            dai.StereoDepthProperties.DepthAlign.RECTIFIED_LEFT
        )
        mono(dai.CameraBoardSocket.CAM_B).out.link(stereo.left)
        mono(dai.CameraBoardSocket.CAM_C).out.link(stereo.right)
        out("left", stereo.rectifiedLeft)
        out("right", stereo.rectifiedRight)
        if self.depth:
            out("depth", stereo.depth)

        if self.has_imu:
            imu = p.create(dai.node.IMU)
            imu.enableIMUSensor(
                [dai.IMUSensor.ACCELEROMETER_RAW, dai.IMUSensor.GYROSCOPE_RAW],
                self.imu_hz,
            )
            imu.setBatchReportThreshold(1)
            imu.setMaxBatchReports(20)
            out("imu", imu.out)
        return p

    def calibration(self) -> StereoCalibration:
        calib = self.device.readCalibration()
        w, h = 640, 400
        # depthai rectifies both mono streams into the right camera's
        # intrinsics
        K = calib.getCameraIntrinsics(dai.CameraBoardSocket.CAM_C, w, h)
        imu_to_left = None
        if self.has_imu:
            T = np.array(
                calib.getImuToCameraExtrinsics(dai.CameraBoardSocket.CAM_B),
                dtype=float,
            )
            T[:3, :3] = R_LEFT_IMU
            T[:3, 3] /= 100  # depthai extrinsics are in cm
            R_rect = np.eye(4)
            R_rect[:3, :3] = (
                calib.getStereoLeftRectificationRotation()
            )  # raw left -> rectified left
            imu_to_left = R_rect @ T
        return StereoCalibration(
            Intrinsics(K[0][0], K[1][1], K[0][2], K[1][2], w, h),
            calib.getBaselineDistance() / 100,
            imu_to_left,
            serial=self.device.getMxId(),
        )

    def get_stereo(self) -> StereoFrame:
        left = self.q_left.get()
        depth = None
        if self.q_depth:
            depth = self.q_depth.get().getFrame().astype(np.float32) / 1000
            depth[depth == 0] = np.nan
        return StereoFrame(
            left.getCvFrame(),
            self.q_right.get().getCvFrame(),
            depth,
            left.getTimestamp().total_seconds(),
        )

    def get_imu(self) -> list[ImuSample]:
        if not self.q_imu:
            return []
        samples = []
        while (data := self.q_imu.tryGet()) is not None:
            for p in data.packets:
                a, g = p.acceleroMeter, p.gyroscope
                samples.append(
                    ImuSample(
                        a.getTimestamp().total_seconds(),
                        np.array([a.x, a.y, a.z]),
                        np.array([g.x, g.y, g.z]),
                    )
                )
        return samples
