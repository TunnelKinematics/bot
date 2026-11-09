# Interfaces

`robot.launch.py` (bot_bringup) is the top-level bringup the container runs. It includes:

- `bot_description/launch/description.launch.py`: `robot_state_publisher` with `bot_description/urdf/bot.urdf.xacro`
  (the robot's static frames, `mount` fed to the xacro args `x y z roll pitch yaw`).
- `lidar.launch.py`: the Unitree driver only (`unitree_lidar_ros2`, built into the image from a pinned commit).
- `slam.launch.py` unless `slam:=false`: lidar-inertial odometry ([Point-LIO, ROS 2 port](https://github.com/dfloreaa/point_lio_ros2),
  built into `/opt/slam` from a pinned commit), `slam_odom`, which re-expresses its IMU pose as `base_link`, and the
  static `map → odom`.
- `foxglove_bridge` on port 8765 unless `foxglove:=false`, serving `/lidar/points`, `/lidar/imu`, `/slam/odom`,
  `/slam/cloud`, `/robot_description`, `/tf` and `/tf_static`.

## Launch arguments

| Argument       | Default        | Launch file    | Effect                                                    |
|----------------|----------------|----------------|-----------------------------------------------------------|
| `mount`        | `0 0 0 0 0 0`  | robot, description | `base_link → lidar_link` as `x y z roll pitch yaw` (m, rad) |
| `slam`         | `true`         | robot          | Include `slam.launch.py`                                   |
| `slam_tf`      | `true`         | slam           | `slam_odom` publishes `odom → base_link`; `false` leaves it to another estimator, `/slam/odom` still publishes |
| `foxglove`     | `true`         | robot          | Start `foxglove_bridge`                                    |
| `use_sim_time` | `false`        | slam           | Bag replay with `ros2 bag play --clock`                    |

## Topics

| Topic                | Type                       | Frame        | Rate          |
|----------------------|----------------------------|--------------|---------------|
| `/lidar/points`      | `sensor_msgs/PointCloud2`  | `lidar_link` | ~12 Hz        |
| `/lidar/imu`         | `sensor_msgs/Imu`          | `lidar_imu_link` | ~250 Hz   |
| `/slam/odom`         | `nav_msgs/Odometry`        | `odom` → child `base_link` | per scan, ~12 Hz |
| `/slam/cloud`        | `sensor_msgs/PointCloud2`  | `odom`       | per scan, deskewed and registered, 0.2 m voxels |
| `/robot_description` | `std_msgs/String`          |              | latched URDF  |

The lidar fields are `x y z intensity ring time`. The driver's own TF (IMU attitude) is remapped to `/lidar/tf`
and Point-LIO's raw outputs (IMU pose in `odom`, its TF) to `/slam/raw/*`; neither is part of the tree.

`/slam/odom` follows REP 105: pose of `base_link` in `odom`, twist in `base_link`. Covariances are not filled.
`odom` is gravity-aligned (z up) with its origin and yaw at the IMU's pose when SLAM started, so `base_link`
starts at minus the mount offset rather than exactly at zero.

## Frames

```
map ──► odom ──► base_link ──► lidar_link ──► lidar_imu_link
```

| Transform                     | Owner                                                   |
|-------------------------------|---------------------------------------------------------|
| `map → odom`                  | Static identity (`slam.launch.py`)                      |
| `odom → base_link`            | `slam_odom`, per scan (until an EKF owns it)            |
| `base_link → lidar_link`      | `robot_state_publisher`, from `mount`                   |
| `lidar_link → lidar_imu_link` | `robot_state_publisher`, factory offset (-0.007698, -0.014655, 0.00667) m |

Point-LIO estimates the IMU (`lidar_imu_link`) pose; `slam_odom` composes it with `lidar_imu_link → base_link`
from TF, so a changed `mount` needs no SLAM config change. REP 103/105: x forward, y left, z up, SI units.

Future seams: a state estimator (EKF fusing leg odometry, IMU and `/slam/odom`) takes over `odom → base_link`
with `slam_tf:=false`; loop closure or relocalization replaces the static `map → odom`. More links (legs, feet)
go into `bot.urdf.xacro`.

## Parameters

| Setting           | Where                                     |
|-------------------|-------------------------------------------|
| Driver parameters | `bot_bringup/config/lidar.yaml`           |
| SLAM parameters   | `bot_bringup/config/slam.yaml`            |
| Robot geometry    | `bot_description/urdf/bot.urdf.xacro`     |
| Topic/frame names | `lidar.launch.py` (`TOPICS`, `FRAMES`), `slam.launch.py` (`REMAPPINGS`) |

Unitree L2 over USB serial at 4000000 baud on `/dev/unitree_lidar` (from `udev/99-unitree-lidar.rules`, CH343 `1a86:55d3`).
The lidar must already be in serial mode (`work_mode` 8). From the factory it ships in Ethernet mode,
and switching it needs an Ethernet connection once (Unilidar 2 or the SDK's `set_to_serial_mode`).

## Jetson runbook

```
cd ~/bot && git pull
sudo cp ros/udev/99-unitree-lidar.rules /etc/udev/rules.d/ && sudo udevadm control --reload-rules && sudo udevadm trigger
zcat /proc/config.gz | grep CONFIG_USB_ACM=   # must be y or m, otherwise no /dev/ttyACM*
ls -l /dev/unitree_lidar                       # with the lidar plugged in and powered
docker compose -f ros/docker/compose.yml up --build -d
docker compose -f ros/docker/compose.yml restart   # if the lidar was plugged in after start; the driver never reopens the port
sudo tailscale serve --bg 8765   # once, persists across reboots; needs HTTPS certificates enabled in the Tailscale admin DNS settings
ros/lidar_view.sh                # prints the Foxglove URL, one sample from each topic, then live rates
```

Keep the lidar still for ~2 s after (re)start while Point-LIO initializes from the IMU.

Foxglove (app.foxglove.dev, on a machine in the tailnet): Connect to a robot → Foxglove WebSocket →
`wss://<jetson>.<tailnet>.ts.net`, then add a 3D panel with display frame `map` and enable `/slam/cloud` with a
large Decay time (e.g. 300 s): the scans accumulate into the map client-side, and it stays fixed while the
`base_link` axes move with the sensor. `/lidar/points` is optional; a rate-limited link drops it first.

## Bags

Host `bags/` (gitignored) is `/ws/bags` in the container.

```
docker exec -it bot /entrypoint.sh ros2 bag record -o /ws/bags/walk1 /lidar/points /lidar/imu /tf_static   # Ctrl-C to stop
```

Replay through SLAM only (stop the live stack first, it shares the ROS domain). The static frames come from the
bag's `/tf_static`, so record it as above:

```
docker compose -f ros/docker/compose.yml stop
docker compose -f ros/docker/compose.yml run --rm --name replay bot bash -c \
  'colcon build --symlink-install && . install/setup.bash && exec ros2 launch bot_bringup slam.launch.py use_sim_time:=true'
docker exec -it replay /entrypoint.sh ros2 bag play /ws/bags/walk1 --clock   # bag path before --clock, which takes an optional rate
```
