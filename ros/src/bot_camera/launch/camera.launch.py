from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    serial_number = LaunchConfiguration('serial_number')
    zed_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [
                    FindPackageShare('zed_wrapper'),
                    'launch',
                    'zed_camera.launch.py',
                ]
            )
        ),
        launch_arguments={
            'camera_model': 'zed2i',
            'camera_name': 'zed',
            'namespace': '',
            'serial_number': serial_number,
            'publish_tf': 'false',
            'publish_map_tf': 'false',
            'publish_imu_tf': 'true',
            'param_overrides': (
                'video.publish_left_right:=true;'
                'video.publish_rgb:=true;'
                'video.publish_gray:=true;'
                'depth.depth_mode:=NEURAL_LIGHT;'
                'depth.depth_stabilization:=0;'
                'depth.publish_depth_map:=true;'
                'sensors.publish_imu_raw:=true;'
                'sensors.publish_cam_imu_transf:=true;'
                'sensors.sensors_pub_rate:=400.0;'
                'pos_tracking.pos_tracking_enabled:=false;'
                'pos_tracking.base_frame:=zed_sdk_base'
            ),
        }.items(),
    )
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                'serial_number',
                default_value='0',
                description='ZED serial number; 0 selects the first camera.',
            ),
            zed_launch,
        ]
    )
