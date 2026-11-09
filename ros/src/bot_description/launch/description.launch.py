import xacro
from ament_index_python.packages import get_package_share_path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

URDF = get_package_share_path('bot_description') / 'urdf' / 'bot.urdf.xacro'
POSE = ['x', 'y', 'z', 'roll', 'pitch', 'yaw']


def nodes(context):
    mount = dict(zip(POSE, LaunchConfiguration('mount').perform(context).split(), strict=True))
    return [Node(
        package='robot_state_publisher', executable='robot_state_publisher', output='screen',
        parameters=[{'robot_description': xacro.process_file(str(URDF), mappings=mount).toxml()}])]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('mount', default_value='0 0 0 0 0 0',
                              description='base_link -> lidar_link as "x y z roll pitch yaw" (m, rad)'),
        OpaqueFunction(function=nodes),
    ])
