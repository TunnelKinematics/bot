from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    serial_number = LaunchConfiguration("serial_number")
    camera = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [
                    FindPackageShare("bot_camera"),
                    "launch",
                    "camera.launch.py",
                ]
            )
        ),
        launch_arguments={"serial_number": serial_number}.items(),
    )
    perception = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [
                    FindPackageShare("bot_perception"),
                    "launch",
                    "perception.launch.py",
                ]
            )
        )
    )
    rosbridge = Node(
        package="rosbridge_server",
        executable="rosbridge_websocket",
        name="rosbridge_websocket",
        output="screen",
        parameters=[{"address": "0.0.0.0", "port": 9090}],
    )
    video = Node(
        package="web_video_server",
        executable="web_video_server",
        name="web_video_server",
        output="screen",
        parameters=[{"address": "0.0.0.0", "port": 8081}],
    )
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "serial_number",
                default_value="0",
                description="ZED serial number; 0 selects the first camera.",
            ),
            camera,
            TimerAction(period=5.0, actions=[perception]),
            rosbridge,
            video,
        ]
    )
