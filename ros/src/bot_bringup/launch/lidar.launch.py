from ament_index_python.packages import get_package_share_path
from launch import LaunchDescription
from launch_ros.actions import Node

CONFIG = get_package_share_path('bot_bringup') / 'config' / 'lidar.yaml'
FRAMES = {'cloud_frame': 'lidar_link', 'imu_frame': 'lidar_imu_link'}
TOPICS = {'cloud_topic': '/lidar/points', 'imu_topic': '/lidar/imu'}


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='unitree_lidar_ros2', executable='unitree_lidar_ros2_node', name='lidar',
            output='screen', parameters=[str(CONFIG), FRAMES | TOPICS],
            # The L2 driver broadcasts its IMU attitude as TF, which would give lidar_link a second parent.
            remappings=[('/tf', '/lidar/tf')]),
    ])
