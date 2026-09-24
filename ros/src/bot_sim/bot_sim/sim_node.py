import rclpy
from rclpy.node import Node


class SimNode(Node):
    def __init__(self):
        super().__init__('sim_node')
        self.get_logger().info('sim_node started (stub)')


def main():
    rclpy.init()
    node = SimNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
