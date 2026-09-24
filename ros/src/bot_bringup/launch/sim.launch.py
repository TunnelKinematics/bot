from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    params = [{'use_sim_time': use_sim_time}]

    nodes = [
        Node(package=f'bot_{name}', executable=f'{name}_node', name=f'{name}_node',
             parameters=params, output='screen')
        for name in ('sim', 'perception', 'planning', 'locomotion')
    ]

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        *nodes,
    ])
