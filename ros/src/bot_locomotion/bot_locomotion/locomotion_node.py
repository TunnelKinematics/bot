import rclpy
from rclpy.node import Node


class LocomotionNode(Node):
    def __init__(self):
        super().__init__('locomotion_node')
        self.get_logger().info('locomotion_node started (stub)')


def main():
    rclpy.init()
    node = LocomotionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
