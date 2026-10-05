# Interfaces

These are the contracts between nodes. A node can be replaced (sim ↔ real, stub ↔
real implementation) as long as it publishes and subscribes to what is listed here.

## Packages

| Package          | Role                                                         |
|------------------|--------------------------------------------------------------|
| `bot_sim`        | MuJoCo simulation. Stands in for the robot hardware and the camera. |
| `bot_camera`     | Launch/configuration for the official ZED ROS 2 wrapper      |
| `bot_perception` | Stereo SLAM (cuVSLAM) and mapping (nvblox)                   |
| `bot_planning`   | Global path and local control → `/cmd_vel`                   |
| `bot_locomotion` | `/cmd_vel` → joint commands (the gait controller)            |
| `bot_bringup`    | Launch files and config. `sim:=true\|false` picks sim or real. |

Robot-specific packages (for example `solo12_description`) live on branches.

## Data flow

```
              /zed/zed_node/*         SLAM + nvblox
 sim|camera ─────────────► perception ────────────► planning
    ▲                                                  │
    │ /joint_commands                                  │ /cmd_vel
    │                                                  ▼
    └──────────────────── locomotion ◄─────────────────┘
          /joint_states, /zed/zed_node/imu/data_raw ──►
```

## TF tree

```
map ──► odom ──► base_link ──► camera_link ──► camera_{left,right}_optical_frame
                     └──► <leg links>   (robot_state_publisher, from /joint_states)
```

| Transform                   | Published by                                        |
|-----------------------------|-----------------------------------------------------|
| `map → odom`                | perception (SLAM loop-closure correction). In the stub, identity. |
| `odom → base_link`          | perception (visual odometry). In the stub, sim ground truth. |
| `base_link → camera_link`   | static, from URDF                                   |
| `base_link → leg links`     | `robot_state_publisher`                             |

Conventions follow REP 103 and REP 105:
- Body frames are x forward, y left, z up.
- Optical frames are z forward, x right, y down.
- Units are SI (m, rad, s).

## Topics

| Topic                          | Type                          | Publisher     | Subscribers         | Rate     |
|--------------------------------|-------------------------------|---------------|---------------------|----------|
| `/clock`                       | `rosgraph_msgs/Clock`         | sim           | all (sim only)      | sim step |
| `/joint_states`                | `sensor_msgs/JointState`      | sim / hw      | locomotion, `robot_state_publisher` | 500 Hz+ |
| `/zed/zed_node/imu/data_raw`   | `sensor_msgs/Imu`             | sim / camera  | locomotion, perception | 400 Hz |
| `/joint_commands`              | `sensor_msgs/JointState` ¹    | locomotion    | sim / hw            | 500 Hz+  |
| `/zed/zed_node/left/gray/rect/image` | `sensor_msgs/Image`     | camera        | cuVSLAM            | 30 Hz    |
| `/zed/zed_node/right/gray/rect/image` | `sensor_msgs/Image`    | camera        | cuVSLAM            | 30 Hz    |
| `/zed/zed_node/depth/depth_registered` | `sensor_msgs/Image` (`32FC1`, meters) | camera | nvblox | 30 Hz |
| `/zed/zed_node/{left,right}/gray/rect/camera_info` | `sensor_msgs/CameraInfo` | camera | cuVSLAM | 30 Hz |
| `/visual_slam/tracking/odometry` | `nav_msgs/Odometry`        | cuVSLAM       | planning           | 30 Hz    |
| `/visual_slam/tracking/slam_path` | `nav_msgs/Path`           | cuVSLAM       | dashboard          | updates  |
| `/visual_slam/vis/landmarks_cloud` | `sensor_msgs/PointCloud2` | cuVSLAM      | dashboard          | updates  |
| `/nvblox_node/mesh`            | `nvblox_msgs/Mesh`            | nvblox        | visualization      | updates  |
| `/nvblox_node/tsdf_layer_marker` | `visualization_msgs/Marker` | nvblox        | dashboard          | updates  |
| `/goal_pose`                   | `geometry_msgs/PoseStamped`   | user          | planning           | on demand |
| `/plan`                        | `nav_msgs/Path`               | planning      | viz, recording      | 1 Hz     |
| `/cmd_vel`                     | `geometry_msgs/Twist`         | planning      | locomotion          | 20–50 Hz |

¹ `/joint_commands` reuses the `JointState` fields: `position` is the target angle (q_des),
`velocity` is the target velocity (dq_des), and `effort` is the feed-forward torque (tau_ff).
The PD gains kp and kd are parameters for now. If per-joint gains per message are needed,
this topic moves to a custom `bot_msgs/JointCommand`.

`/cmd_vel` is interpreted in `base_link`: `linear.x` and `linear.y` are the body velocity and
`angular.z` is the yaw rate. Other fields are ignored.

## Sim vs real

- With `sim:=true`, every node sets `use_sim_time:=true` and `bot_sim` publishes `/clock`.
- `bot_sim` loads its model from the `model_path` parameter (MJCF or URDF), so it has no
  robot-specific code.
- The real camera and hardware nodes must collectively publish and subscribe
  to the same topics as `bot_sim`.

## Live visualization

Run `./scripts/start_live.sh` on the Jetson. The first run builds the pinned
Isaac ROS 3.2, ROS 2 Humble, and ZED 5.3.1 image for JetPack 6. It then starts
the ZED 2i, GPU-accelerated cuVSLAM and nvblox, browser bridges, and dashboard,
and prints a Tailscale URL such as `http://100.x.y.z:8080`. Later runs reuse
the image. Re-run `./scripts/build_jetson.sh` after changing the Dockerfile.
