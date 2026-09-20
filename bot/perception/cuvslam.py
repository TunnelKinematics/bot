"""Stereo(-inertial) SLAM with NVIDIA cuVSLAM.

https://github.com/nvidia-isaac/cuVSLAM - GPU only; modal_app.py runs it
off-robot.
"""

import warnings

import cuvslam as vslam
import numpy as np
from scipy.spatial.transform import Rotation

from ..common.types import T_BODY_OPTICAL, Pose
from ..sensors.types import ImuSample, StereoCalibration, StereoFrame

# Consumer-grade IMU noise; only weights IMU factors against visual ones.
IMU_NOISE = dict(
    gyroscope_noise_density=0.00016,
    gyroscope_random_walk=0.000022,
    accelerometer_noise_density=0.0028,
    accelerometer_random_walk=0.00086,
)


def _matrix(rotation_xyzw, translation) -> np.ndarray:
    T = np.eye(4)
    T[:3, :3] = Rotation.from_quat(rotation_xyzw).as_matrix()
    T[:3, 3] = translation
    return T


def _vslam_pose(T: np.ndarray) -> vslam.Pose:
    return vslam.Pose(
        rotation=Rotation.from_matrix(T[:3, :3]).as_quat().tolist(),
        translation=T[:3, 3].tolist(),
    )


class Cuvslam:
    """One cuVSLAM rig built from N rectified stereo pairs.

    All frames of a rig must be hardware-synchronized within ~1 ms. The rig
    frame is the first pair's left optical frame; poses are returned in the
    body frame (x forward, y left, z up), world = body frame at the first
    frame. Keyframes for the mapper are flagged by motion (keyframe_dist /
    keyframe_angle).
    """

    def __init__(
        self,
        calibs: list[StereoCalibration],
        imu_hz: float = 200,
        keyframe_dist: float = 0.1,
        keyframe_angle: float = np.radians(10),
        planar: bool = False,
        loop_closure: bool = True,
    ):
        cameras, imus = [], []
        for c in calibs:
            i = c.intrinsics
            right = np.eye(4)
            right[0, 3] = c.baseline
            pinhole = vslam.Distortion(vslam.Distortion.Model.Pinhole, [])
            for T in (c.left_to_rig, c.left_to_rig @ right):
                cameras.append(
                    vslam.Camera(
                        size=(i.width, i.height),
                        principal=(i.cx, i.cy),
                        focal=(i.fx, i.fy),
                        rig_from_camera=_vslam_pose(T),
                        distortion=pinhole,
                    )
                )
            if c.imu_to_left is not None and not imus:  # cuVSLAM takes one IMU
                imus.append(
                    vslam.ImuCalibration(
                        rig_from_imu=_vslam_pose(
                            c.left_to_rig @ c.imu_to_left
                        ),
                        frequency=imu_hz,
                        **IMU_NOISE,
                    )
                )
        if not imus:
            warnings.warn(
                "no IMU extrinsics in calibration: visual-only odometry, "
                "no gravity alignment",
                stacklevel=2,
            )
        self.rig = vslam.Rig(cameras=cameras, imus=imus)
        # async_sba=False + sync_mode=True: everything in the calling thread,
        # so results are final and reproducible
        self.odom_cfg = vslam.Tracker.OdometryConfig(
            odometry_mode=vslam.Tracker.OdometryMode.Inertial
            if imus
            else vslam.Tracker.OdometryMode.Multicamera,
            rectified_stereo_camera=True,
            async_sba=False,
        )
        self.slam_cfg = (
            vslam.Tracker.SlamConfig(sync_mode=True, planar_constraints=planar)
            if loop_closure
            else None
        )
        self.keyframe_dist, self.keyframe_angle = keyframe_dist, keyframe_angle
        self.reset()

    def reset(self) -> None:
        self.tracker = vslam.Tracker(self.rig, self.odom_cfg, self.slam_cfg)
        self.keyframes: list[
            tuple[np.ndarray, float]
        ] = []  # T_world_rig, timestamp
        self.T_world_rig = np.eye(4)
        # World correction making gravity -z. Identity until the IMU has
        # estimated gravity; fixed from then on so the live map frame is
        # stable. Visual-only rigs have nothing to wait for.
        self.T_level = np.eye(4)
        self.initialized = not self.rig.imus
        self.tracked = self.is_keyframe = False

    def track(self, frames: list[StereoFrame], imu: list[ImuSample]) -> Pose:
        """One synchronized frame per stereo pair, in rig order, plus the
        IMU samples since the last call."""
        for s in imu if self.rig.imus else []:
            self.tracker.register_imu_measurement(
                0,
                vslam.ImuMeasurement(
                    timestamp_ns=int(s.timestamp * 1e9),
                    linear_accelerations=s.accel,
                    angular_velocities=s.gyro,
                ),
            )
        ts = frames[0].timestamp
        estimate, _ = self.tracker.track(
            int(ts * 1e9), [im for f in frames for im in (f.left, f.right)]
        )
        self.tracked = estimate.world_from_rig is not None
        self.is_keyframe = False
        if self.tracked:
            p = estimate.world_from_rig.pose
            self.T_world_rig = _matrix(p.rotation, p.translation)
            if not self.initialized:
                self.initialized = self._level()
            self.is_keyframe = self.initialized and (
                not self.keyframes
                or self._moved(
                    np.linalg.inv(self.keyframes[-1][0]) @ self.T_world_rig
                )
            )
            if self.is_keyframe:
                self.keyframes.append((self.T_world_rig.copy(), ts))
        return self._pose(self.T_world_rig, ts)

    def _level(self) -> bool:
        """Sets T_level from cuVSLAM's current gravity estimate (rig frame);
        False until the IMU has one."""
        g = self.tracker.get_last_gravity()
        if g is None:
            return False
        g_body = (
            T_BODY_OPTICAL[:3, :3] @ self.T_world_rig[:3, :3] @ np.asarray(g)
        )
        R = Rotation.align_vectors([[0, 0, -1]], [g_body])[0].as_matrix()
        self.T_level = np.eye(4)
        self.T_level[:3, :3] = R
        return True

    def _moved(self, T: np.ndarray) -> bool:
        angle = np.arccos(np.clip((np.trace(T[:3, :3]) - 1) / 2, -1, 1))
        return (
            np.linalg.norm(T[:3, 3]) > self.keyframe_dist
            or angle > self.keyframe_angle
        )

    def _pose(self, T_world_rig: np.ndarray, ts: float) -> Pose:
        T = T_BODY_OPTICAL @ T_world_rig @ np.linalg.inv(T_BODY_OPTICAL)
        return Pose.from_matrix(self.T_level @ T, ts)

    def optimize(self) -> list[Pose]:
        """Loop-closed keyframe poses from cuVSLAM's pose graph, with world
        z aligned to gravity when an IMU is present."""
        if self.slam_cfg is not None:
            slam = {
                ps.timestamp_ns: _matrix(ps.pose.rotation, ps.pose.translation)
                for ps in self.tracker.get_all_slam_poses()
            }
            stamps = np.array(sorted(slam))

            def nearest(ts):
                return slam[stamps[np.abs(stamps - int(ts * 1e9)).argmin()]]

            self.keyframes = [
                (
                    nearest(ts)
                    if np.abs(stamps - int(ts * 1e9)).min() < 1e6
                    else T,
                    ts,
                )
                for T, ts in self.keyframes
            ]
        if self.rig.imus:
            self._level()  # the estimate has been refined over the whole run
        return [self._pose(T, ts) for T, ts in self.keyframes]
