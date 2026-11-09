from ament_index_python.packages import get_package_share_path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

CONFIG = get_package_share_path('bot_bringup') / 'config' / 'slam.yaml'
RAW = ['tf', 'path', 'Laser_map', 'cloud_effected', 'cloud_registered_body']
REMAPPINGS = [('/cloud_registered', '/slam/cloud'), ('/aft_mapped_to_init', '/slam/raw/odom')] \
    + [(f'/{topic}', f'/slam/raw/{topic}') for topic in RAW]


def generate_launch_description():
    sim = {'use_sim_time': LaunchConfiguration('use_sim_time')}
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false', choices=['true', 'false']),
        DeclareLaunchArgument('slam_tf', default_value='true', choices=['true', 'false'],
                              description='publish odom -> base_link (false when a state estimator owns it)'),
        Node(
            package='point_lio', executable='pointlio_mapping', name='slam', output='screen',
            parameters=[str(CONFIG), sim], remappings=REMAPPINGS),
        Node(
            package='bot_bringup', executable='slam_odom.py', name='slam_odom', output='screen',
            parameters=[sim, {'publish_tf': LaunchConfiguration('slam_tf')}]),
        Node(
            package='tf2_ros', executable='static_transform_publisher', name='odom_tf', parameters=[sim],
            arguments=['--frame-id', 'map', '--child-frame-id', 'odom']),
    ])
