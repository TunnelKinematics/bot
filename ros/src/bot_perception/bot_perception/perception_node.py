import rclpy
from rclpy.node import Node


class PerceptionNode(Node):
    def __init__(self):
        super().__init__("perception_node")
        self.get_logger().info("perception_node started (stub)")


def main():
    rclpy.init()
    node = PerceptionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
