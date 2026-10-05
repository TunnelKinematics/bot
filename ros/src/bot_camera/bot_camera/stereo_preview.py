from array import array

import numpy as np
import rclpy
from message_filters import Subscriber, TimeSynchronizer
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


def pixels(image):
    rows = np.frombuffer(image.data, np.uint8).reshape(image.height, -1)
    return rows[:, :image.width]


class StereoPreview(Node):
    """Joins synchronized mono8 left/right frames into one image."""

    def __init__(self):
        super().__init__('stereo_preview')
        self.stride = self.declare_parameter('stride', 2).value
        self.count = 0
        self.publisher = self.create_publisher(Image, 'stereo_preview', 1)
        cameras = [
            Subscriber(self, Image, topic, qos_profile=qos_profile_sensor_data)
            for topic in ('left', 'right')
        ]
        TimeSynchronizer(cameras, 4).registerCallback(self.join)

    def join(self, left, right):
        self.count += 1
        if self.count % self.stride:
            return
        joined = np.hstack((pixels(left), pixels(right)))
        self.publisher.publish(Image(
            header=left.header,
            height=joined.shape[0],
            width=joined.shape[1],
            encoding='mono8',
            step=joined.shape[1],
            data=array('B', joined.tobytes()),
        ))


def main():
    rclpy.init()
    node = StereoPreview()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
