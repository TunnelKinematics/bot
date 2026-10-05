from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import (
    Command,
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.actions import LoadComposableNodes, Node
from launch_ros.descriptions import ComposableNode
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    serial_number = LaunchConfiguration('serial_number')
    container_name = LaunchConfiguration('container_name')
    zed_config = FindPackageShare('zed_wrapper')

    description = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        namespace='zed',
        name='zed_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': Command([
                'xacro ',
                PathJoinSubstitution(
                    [zed_config, 'urdf', 'zed_descr.urdf.xacro']
                ),
                ' camera_name:=zed camera_model:=zed2i',
            ]),
        }],
        remappings=[('robot_description', 'zed_description')],
    )

    # The ZED wrapper launch always targets a container inside the camera
    # namespace, so the node is loaded directly to share the NITROS container.
    zed = ComposableNode(
        package='zed_components',
        plugin='stereolabs::ZedCamera',
        namespace='zed',
        name='zed_node',
        parameters=[
            PathJoinSubstitution([zed_config, 'config', 'common_stereo.yaml']),
            PathJoinSubstitution([zed_config, 'config', 'zed2i.yaml']),
            {
                'general.camera_name': 'zed',
                'general.camera_model': 'zed2i',
                'general.serial_number': serial_number,
                'general.grab_frame_rate': 30,
                'general.pub_resolution': 'CUSTOM',
                'general.pub_downscale_factor': 2.0,
                # With NITROS, left/right gray topics exist only under
                # publish_left_right.
                'video.publish_left_right': True,
                'video.publish_gray': True,
                'depth.publish_point_cloud': False,
            },
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                'serial_number',
                default_value='0',
                description='ZED serial number; 0 selects the first camera.',
            ),
            DeclareLaunchArgument(
                'container_name',
                description='Component container shared with NITROS consumers.',
            ),
            description,
            LoadComposableNodes(
                target_container=container_name,
                composable_node_descriptions=[zed],
            ),
        ]
    )
