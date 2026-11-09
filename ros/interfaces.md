# Interfaces

`bot_bringup/launch/lidar.launch.py` runs the Unitree driver (`unitree_lidar_ros2`, built into the
image from a pinned commit) and the static transforms below. `slam.launch.py` runs lidar-inertial odometry
([Point-LIO, ROS 2 port](https://github.com/dfloreaa/point_lio_ros2), built into `/opt/slam` from a pinned
commit) plus `slam_bridge`, which re-expresses its IMU pose as `base_link` and builds the viewer map.
`robot.launch.py` is the top-level bringup the container runs: it includes `lidar.launch.py` (same `model` and
`mount` args), `slam.launch.py` unless `slam:=false`, and, unless `foxglove:=false`, `foxglove_bridge` on
port 8765 serving `/lidar/points`, `/lidar/imu`, `/slam/{odom,cloud,map,path}`, `/tf` and `/tf_static`.

## Topics

| Topic           | Type                       | Frame        | Rate          |
|-----------------|----------------------------|--------------|---------------|
| `/lidar/points` | `sensor_msgs/PointCloud2`  | `lidar_link` | ~12 Hz        |
| `/lidar/imu`    | `sensor_msgs/Imu`          | `lidar_imu_link` | ~250 Hz (L2) |
| `/slam/odom`    | `nav_msgs/Odometry`        | `odom` → child `base_link` | per scan, ~12 Hz |
| `/slam/cloud`   | `sensor_msgs/PointCloud2`  | `odom`       | per scan, deskewed and registered, 0.2 m voxels |
| `/slam/map`     | `sensor_msgs/PointCloud2`  | `odom`       | 1 Hz, accumulated, 0.1 m voxels, latched |
| `/slam/path`    | `nav_msgs/Path`            | `odom`       | 1 Hz, `base_link` every 5 cm, latched |

The lidar fields are `x y z intensity ring time`. The driver's own TF (IMU attitude) is remapped to `/lidar/tf`
and Point-LIO's raw outputs (IMU pose in `odom`, its TF) to `/slam/raw/*`; neither is part of the tree.

`/slam/odom` follows REP 105: pose of `base_link` in `odom`, twist in `base_link`. Covariances are not filled.
`odom` is gravity-aligned (z up) with its origin and yaw at the IMU's pose when SLAM started, so `base_link`
starts at minus the mount offset rather than exactly at zero. The map lives in memory and resets on restart.

## Frames

```
map ──► odom ──► base_link ──► lidar_link ──► lidar_imu_link
```

| Transform                     | Source                                                  |
|-------------------------------|---------------------------------------------------------|
| `map → odom`                  | Static identity (`slam.launch.py`). Reserved for loop closure / relocalization. |
| `odom → base_link`            | `slam_bridge`, per scan                                 |
| `base_link → lidar_link`      | launch arg `mount:="x y z roll pitch yaw"`, zero by default. A URDF replaces this later. |
| `lidar_link → lidar_imu_link` | Factory offset (-0.007698, -0.014655, 0.00667) m        |

Point-LIO estimates the IMU (`lidar_imu_link`) pose; `slam_bridge` composes it with `lidar_imu_link → base_link`
from TF, so a changed `mount` needs no SLAM config change. REP 103/105: x forward, y left, z up, SI units.

## Parameters

| Setting           | Where                                     |
|-------------------|-------------------------------------------|
| Lidar model       | `LIDAR_MODEL=l2\|l1`: a Docker build arg, also the default of the launch arg `model` |
| Driver parameters | `bot_bringup/config/lidar_<model>.yaml`   |
| SLAM parameters   | `bot_bringup/config/slam_<model>.yaml` (L2 only for now; `slam:=false` for L1) |
| Topic/frame names | `lidar.launch.py` (`TOPICS`, `FRAMES`), `slam.launch.py` (`REMAPPINGS`) |

L2: USB serial at 4000000 baud on `/dev/unitree_lidar` (from `udev/99-unitree-lidar.rules`, CH343 `1a86:55d3`).
The lidar must already be in serial mode (`work_mode` 8). From the factory it ships in Ethernet mode,
and switching it needs an Ethernet connection once (Unilidar 2 or the SDK's `set_to_serial_mode`).
L1: `/dev/ttyUSB0`.

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
`wss://<jetson>.<tailnet>.ts.net`, then add a 3D panel with display frame `map` and enable `/slam/map`
(decay time 0) and `/slam/cloud` (or `/lidar/points`), plus `/slam/path` if wanted. Under Transforms keep `base_link`
visible: the map stays fixed while the `base_link` axes move with the sensor. A rate-limited link drops
`/lidar/points` first; `/slam/map` is small and latched, so it appears as soon as the panel subscribes.

## Bags

Host `bags/` (gitignored) is `/ws/bags` in the container.

```
docker exec -it bot /entrypoint.sh ros2 bag record -o /ws/bags/walk1 /lidar/points /lidar/imu /tf_static   # Ctrl-C to stop
```

Replay through SLAM only (stop the live stack first, it shares the ROS domain):

```
docker compose -f ros/docker/compose.yml stop
docker compose -f ros/docker/compose.yml run --rm --name replay bot bash -c \
  'colcon build --symlink-install && . install/setup.bash && exec ros2 launch bot_bringup slam.launch.py use_sim_time:=true'
docker exec -it replay /entrypoint.sh ros2 bag play /ws/bags/walk1 --clock   # bag path before --clock, which takes an optional rate
```
