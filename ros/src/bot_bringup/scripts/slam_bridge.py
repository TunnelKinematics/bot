#!/usr/bin/env python3
import numpy as np
import rclpy
from geometry_msgs.msg import PoseStamped, TransformStamped
from nav_msgs.msg import Odometry, Path
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from rclpy.time import Time
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py.point_cloud2 import create_cloud_xyz32, read_points_numpy
from tf2_ros import Buffer, TransformBroadcaster, TransformException, TransformListener

LATCHED = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
BITS = 21
OFFSET = 1 << (BITS - 1)
MASK = (1 << BITS) - 1


def vec(m, keys='xyz'):
    return np.array([getattr(m, k) for k in keys])


def assign(m, values, keys='xyzw'):
    for k, v in zip(keys, values):
        setattr(m, k, float(v))


def qmul(a, b):
    return np.append(a[3] * b[:3] + b[3] * a[:3] + np.cross(a[:3], b[:3]), a[3] * b[3] - a[:3] @ b[:3])


def rotate(q, v):
    t = 2 * np.cross(q[:3], v)
    return v + q[3] * t + np.cross(q[:3], t)


def inverse(q):
    return q * [-1, -1, -1, 1]


class SlamBridge(Node):
    def __init__(self):
        super().__init__('slam_bridge')
        self.base = self.declare_parameter('base_frame', 'base_link').value
        self.voxel = self.declare_parameter('map_voxel', 0.1).value
        self.path_step = self.declare_parameter('path_step', 0.05).value
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.tf = TransformBroadcaster(self)
        self.extrinsic = None
        self.keys = np.empty(0, np.int64)
        self.pending = []
        self.cloud_header = None
        self.path = Path()
        self.path_changed = False
        self.odom_pub = self.create_publisher(Odometry, '/slam/odom', 10)
        self.map_pub = self.create_publisher(PointCloud2, '/slam/map', LATCHED)
        self.path_pub = self.create_publisher(Path, '/slam/path', LATCHED)
        self.create_subscription(Odometry, '/slam/raw/odom', self.on_odom, 100)
        self.create_subscription(PointCloud2, '/slam/cloud', self.on_cloud, 10)
        self.create_timer(self.declare_parameter('map_period', 1.0).value, self.publish_map)

    def on_odom(self, msg):
        if self.extrinsic is None:
            try:
                t = self.tf_buffer.lookup_transform(msg.child_frame_id, self.base, Time()).transform
            except TransformException:
                return
            self.extrinsic = vec(t.translation), vec(t.rotation, 'xyzw')
        p_ib, q_ib = self.extrinsic
        pose, twist = msg.pose.pose, msg.twist.twist
        q_oi = vec(pose.orientation, 'xyzw')
        p = vec(pose.position) + rotate(q_oi, p_ib)
        q = qmul(q_oi, q_ib)
        w_i = vec(twist.angular)
        v_i = rotate(inverse(q_oi), vec(twist.linear)) + np.cross(w_i, p_ib)
        assign(pose.position, p)
        assign(pose.orientation, q)
        assign(twist.linear, rotate(inverse(q_ib), v_i))
        assign(twist.angular, rotate(inverse(q_ib), w_i))
        msg.child_frame_id = self.base
        self.odom_pub.publish(msg)
        tf = TransformStamped(header=msg.header, child_frame_id=self.base)
        assign(tf.transform.translation, p)
        assign(tf.transform.rotation, q)
        self.tf.sendTransform(tf)
        if not self.path.poses or np.linalg.norm(p - vec(self.path.poses[-1].pose.position)) > self.path_step:
            self.path.header = msg.header
            self.path.poses.append(PoseStamped(header=msg.header, pose=pose))
            self.path_changed = True

    def on_cloud(self, msg):
        k = np.floor(read_points_numpy(msg, ('x', 'y', 'z'), skip_nans=True) / self.voxel).astype(np.int64) + OFFSET
        self.pending.append((k[:, 0] << 2 * BITS) | (k[:, 1] << BITS) | k[:, 2])
        self.cloud_header = msg.header

    def publish_map(self):
        if self.pending:
            self.keys = np.unique(np.concatenate([self.keys, *self.pending]))
            self.pending.clear()
            k = np.stack([self.keys >> 2 * BITS, self.keys >> BITS & MASK, self.keys & MASK], 1) - OFFSET + 0.5
            self.map_pub.publish(create_cloud_xyz32(self.cloud_header, (k * self.voxel).astype(np.float32)))
        if self.path_changed:
            self.path_pub.publish(self.path)
            self.path_changed = False


def main():
    rclpy.init()
    try:
        rclpy.spin(SlamBridge())
    except (KeyboardInterrupt, ExternalShutdownException):
        pass


if __name__ == '__main__':
    main()
