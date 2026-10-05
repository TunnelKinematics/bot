from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


CONTAINER = "perception_container"


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
        launch_arguments={
            "serial_number": serial_number,
            "container_name": CONTAINER,
        }.items(),
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
        ),
        launch_arguments={"container_name": CONTAINER}.items(),
    )
    rosbridge = Node(
        package="rosbridge_server",
        executable="rosbridge_websocket",
        name="rosbridge_websocket",
        output="screen",
        parameters=[{"address": "0.0.0.0", "port": 9090}],
    )
    stereo_preview = Node(
        package="bot_camera",
        executable="stereo_preview",
        name="stereo_preview",
        output="screen",
        remappings=[
            ("left", "/zed/zed_node/left/gray/rect/image"),
            ("right", "/zed/zed_node/right/gray/rect/image"),
            ("stereo_preview", "/zed/stereo_preview"),
        ],
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
            perception,
            rosbridge,
            stereo_preview,
            video,
        ]
    )
