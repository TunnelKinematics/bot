#!/usr/bin/env python3
import numpy as np
import rclpy
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformBroadcaster, TransformException, TransformListener


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


class SlamOdom(Node):
    def __init__(self):
        super().__init__('slam_odom')
        self.base = self.declare_parameter('base_frame', 'base_link').value
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.tf = TransformBroadcaster(self) if self.declare_parameter('publish_tf', True).value else None
        self.extrinsic = None
        self.odom_pub = self.create_publisher(Odometry, '/slam/odom', 10)
        self.create_subscription(Odometry, '/slam/raw/odom', self.on_odom, 100)

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
        if self.tf is None:
            return
        tf = TransformStamped(header=msg.header, child_frame_id=self.base)
        assign(tf.transform.translation, p)
        assign(tf.transform.rotation, q)
        self.tf.sendTransform(tf)


def main():
    rclpy.init()
    try:
        rclpy.spin(SlamOdom())
    except (KeyboardInterrupt, ExternalShutdownException):
        pass


if __name__ == '__main__':
    main()
