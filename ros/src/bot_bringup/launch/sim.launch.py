from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node, SetParameter
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    params = [{'use_sim_time': use_sim_time}]

    nodes = [
        Node(package=f'bot_{name}', executable=f'{name}_node', name=f'{name}_node',
             parameters=params, output='screen')
        for name in ('sim', 'planning', 'locomotion')
    ]
    perception = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('bot_perception'),
                'launch',
                'perception.launch.py',
            ])
        )
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        *nodes,
        GroupAction([
            SetParameter(name='use_sim_time', value=use_sim_time),
            perception,
        ]),
    ])
