from launch import LaunchDescription
from launch.actions import GroupAction, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import ComposableNodeContainer, SetParameter, SetRemap
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
                "enable_slam_visualization": True,
                "enable_landmarks_view": True,
                "enable_observations_view": False,
                "camera_optical_frames": [
                    "zed_left_camera_frame_optical",
                    "zed_right_camera_frame_optical",
                ],
                "base_frame": "zed_camera_link",
                "num_cameras": 2,
                "enable_imu_fusion": True,
                "imu_frame": "zed_imu_link",
                "gyro_noise_density": 0.000244,
                "gyro_random_walk": 0.000019393,
                "accel_noise_density": 0.001862,
                "accel_random_walk": 0.003,
                "calibration_frequency": 400.0,
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
            ("/visual_slam/imu", "/zed/zed_node/imu/data_raw"),
        ],
    )
    cuvslam_container = ComposableNodeContainer(
        package="rclcpp_components",
        executable="component_container_mt",
        name="cuvslam_container",
        namespace="",
        output="screen",
        composable_node_descriptions=[cuvslam],
    )

    nvblox = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [
                    FindPackageShare("nvblox_examples_bringup"),
                    "launch",
                    "perception",
                    "nvblox.launch.py",
                ]
            )
        ),
        launch_arguments={
            "camera": "zed2",
            "mode": "static",
            "num_cameras": "1",
            "lidar": "False",
            "container_name": "cuvslam_container",
            "run_standalone": "False",
        }.items(),
    )

    nvblox_with_cuvslam_pose = GroupAction(
        [
            SetParameter(
                name="layer_streamer_bandwidth_limit_mbps",
                value=30.0,
            ),
            SetRemap(
                src="/zed/zed_node/pose",
                dst="/visual_slam/tracking/vo_pose",
            ),
            SetRemap(
                src="/zed/zed_node/rgb/image_rect_color",
                dst="/zed/zed_node/rgb/color/rect/image",
            ),
            SetRemap(
                src="/zed/zed_node/rgb/camera_info",
                dst="/zed/zed_node/rgb/color/rect/camera_info",
            ),
            nvblox,
        ]
    )
    return LaunchDescription(
        [cuvslam_container, nvblox_with_cuvslam_pose]
    )
