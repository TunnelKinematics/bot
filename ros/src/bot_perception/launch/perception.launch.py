from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    cuvslam = ComposableNode(
        package="isaac_ros_visual_slam",
        plugin="nvidia::isaac_ros::visual_slam::VisualSlamNode",
        name="visual_slam_node",
        parameters=[
            {
                "rectified_images": True,
                "enable_image_denoising": False,
                "camera_optical_frames": [
                    "zed_left_camera_frame_optical",
                    "zed_right_camera_frame_optical",
                ],
                "base_frame": "zed_camera_link",
                "num_cameras": 2,
                "image_jitter_threshold_ms": 35.0,
            }
        ],
        remappings=[
            (
                "/visual_slam/image_0",
                "/zed/zed_node/left/gray/rect/image",
            ),
            (
                "/visual_slam/camera_info_0",
                "/zed/zed_node/left/gray/rect/camera_info",
            ),
            (
                "/visual_slam/image_1",
                "/zed/zed_node/right/gray/rect/image",
            ),
            (
                "/visual_slam/camera_info_1",
                "/zed/zed_node/right/gray/rect/camera_info",
            ),
        ],
    )

    nvblox_config = PathJoinSubstitution(
        [FindPackageShare("nvblox_examples_bringup"), "config", "nvblox"]
    )
    nvblox = ComposableNode(
        package="nvblox_ros",
        plugin="nvblox::NvbloxNode",
        name="nvblox_node",
        parameters=[
            PathJoinSubstitution([nvblox_config, "nvblox_base.yaml"]),
            PathJoinSubstitution(
                [nvblox_config, "specializations", "nvblox_zed.yaml"]
            ),
            {
                "pose_frame": "zed_camera_link",
                "layer_streamer_bandwidth_limit_mbps": 2.0,
            },
        ],
        remappings=[
            ("camera_0/depth/image", "/zed/zed_node/depth/depth_registered"),
            ("camera_0/depth/camera_info", "/zed/zed_node/depth/camera_info"),
            ("camera_0/color/image", "/zed/zed_node/rgb/color/rect/image"),
            (
                "camera_0/color/camera_info",
                "/zed/zed_node/rgb/color/rect/camera_info",
            ),
        ],
    )

    container = ComposableNodeContainer(
        package="rclcpp_components",
        executable="component_container_mt",
        name=LaunchConfiguration("container_name"),
        namespace="",
        output="screen",
        composable_node_descriptions=[cuvslam, nvblox],
    )
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "container_name",
                default_value="perception_container",
                description="NITROS container that sensors load into.",
            ),
            container,
        ]
    )
