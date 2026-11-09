from ament_index_python.packages import get_package_share_path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

LAUNCH = get_package_share_path('bot_bringup') / 'launch'
DESCRIPTION = get_package_share_path('bot_description') / 'launch' / 'description.launch.py'
FOXGLOVE = {
    'port': 8765,
    'address': '0.0.0.0',
    'topic_whitelist': ['^/lidar/(points|imu)$', '^/slam/(odom|cloud)$', '^/robot_description$', '^/tf(_static)?$'],
}


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('mount', default_value='0 0 0 0 0 0',
                              description='base_link -> lidar_link as "x y z roll pitch yaw" (m, rad)'),
        DeclareLaunchArgument('foxglove', default_value='true', choices=['true', 'false']),
        DeclareLaunchArgument('slam', default_value='true', choices=['true', 'false']),
        IncludeLaunchDescription(str(DESCRIPTION)),
        IncludeLaunchDescription(str(LAUNCH / 'lidar.launch.py')),
        IncludeLaunchDescription(str(LAUNCH / 'slam.launch.py'), condition=IfCondition(LaunchConfiguration('slam'))),
        Node(
            package='foxglove_bridge', executable='foxglove_bridge', name='foxglove_bridge',
            output='screen', parameters=[FOXGLOVE], condition=IfCondition(LaunchConfiguration('foxglove'))),
    ])
