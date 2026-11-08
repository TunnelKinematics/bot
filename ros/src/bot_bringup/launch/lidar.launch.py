from ament_index_python.packages import get_package_share_path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import EnvironmentVariable, LaunchConfiguration
from launch_ros.actions import Node

FRAMES = {'cloud_frame': 'lidar_link', 'imu_frame': 'lidar_imu_link'}
TOPICS = {'cloud_topic': '/lidar/points', 'imu_topic': '/lidar/imu'}


def static_tf(parent, child, x=0, y=0, z=0, roll=0, pitch=0, yaw=0):
    pose = dict(x=x, y=y, z=z, roll=roll, pitch=pitch, yaw=yaw)
    return Node(
        package='tf2_ros', executable='static_transform_publisher', name=f'{child}_tf',
        arguments=[a for k, v in pose.items() for a in (f'--{k}', str(v))]
        + ['--frame-id', parent, '--child-frame-id', child])


def nodes(context):
    model = LaunchConfiguration('model').perform(context)
    mount = LaunchConfiguration('mount').perform(context).split()
    config = get_package_share_path('bot_bringup') / 'config' / f'lidar_{model}.yaml'
    return [
        Node(
            package='unitree_lidar_ros2', executable='unitree_lidar_ros2_node', name='lidar',
            output='screen', parameters=[str(config), FRAMES | TOPICS],
            # The L2 driver broadcasts its IMU attitude as TF, which would give lidar_link a second parent.
            remappings=[('/tf', '/lidar/tf')]),
        static_tf('base_link', FRAMES['cloud_frame'], *mount),
        static_tf(FRAMES['cloud_frame'], FRAMES['imu_frame'], -0.007698, -0.014655, 0.00667),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('model', default_value=EnvironmentVariable('LIDAR_MODEL', default_value='l2'),
                              choices=['l1', 'l2']),
        DeclareLaunchArgument('mount', default_value='0 0 0 0 0 0',
                              description='base_link -> lidar_link as "x y z roll pitch yaw" (m, rad)'),
        OpaqueFunction(function=nodes),
    ])
