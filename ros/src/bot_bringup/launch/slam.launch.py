from ament_index_python.packages import get_package_share_path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import EnvironmentVariable, LaunchConfiguration
from launch_ros.actions import Node

CONFIG = get_package_share_path('bot_bringup') / 'config'
RAW = ['tf', 'path', 'Laser_map', 'cloud_effected', 'cloud_registered_body']
REMAPPINGS = [('/cloud_registered', '/slam/cloud'), ('/aft_mapped_to_init', '/slam/raw/odom')] \
    + [(f'/{topic}', f'/slam/raw/{topic}') for topic in RAW]


def generate_launch_description():
    sim = {'use_sim_time': LaunchConfiguration('use_sim_time')}
    return LaunchDescription([
        DeclareLaunchArgument('model', default_value=EnvironmentVariable('LIDAR_MODEL', default_value='l2')),
        DeclareLaunchArgument('use_sim_time', default_value='false', choices=['true', 'false']),
        Node(
            package='point_lio', executable='pointlio_mapping', name='slam', output='screen',
            parameters=[[str(CONFIG / 'slam_'), LaunchConfiguration('model'), '.yaml'], sim],
            remappings=REMAPPINGS),
        Node(package='bot_bringup', executable='slam_bridge.py', name='slam_bridge', output='screen',
             parameters=[sim]),
        Node(
            package='tf2_ros', executable='static_transform_publisher', name='odom_tf', parameters=[sim],
            arguments=['--frame-id', 'map', '--child-frame-id', 'odom']),
    ])
