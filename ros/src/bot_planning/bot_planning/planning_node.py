import rclpy
from rclpy.node import Node


class PlanningNode(Node):
    def __init__(self):
        super().__init__("planning_node")
        self.get_logger().info("planning_node started (stub)")


def main():
    rclpy.init()
    node = PlanningNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
