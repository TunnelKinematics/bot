# Interfaces

`bot_bringup/launch/lidar.launch.py` runs the Unitree driver (`unitree_lidar_ros2`, built into the
image from a pinned commit) and the static transforms below. Later stacks (for example
`slam.launch.py`) go next to it and consume these topics and frames.

## Topics

| Topic           | Type                       | Rate          |
|-----------------|----------------------------|---------------|
| `/lidar/points` | `sensor_msgs/PointCloud2`  | ~10 Hz        |
| `/lidar/imu`    | `sensor_msgs/Imu`          | ~200 Hz (L2)  |

The fields are `x y z intensity ring time`. The driver's own TF (IMU attitude) is remapped to `/lidar/tf`
and is not part of the tree.

## Frames

```
base_link ──► lidar_link ──► lidar_imu_link
```

| Transform                     | Source                                                  |
|-------------------------------|---------------------------------------------------------|
| `base_link → lidar_link`      | launch arg `mount:="x y z roll pitch yaw"`, zero by default. A URDF replaces this later. |
| `lidar_link → lidar_imu_link` | Factory offset (-0.007698, -0.014655, 0.00667) m        |

REP 103/105: x forward, y left, z up, SI units.

## Parameters

| Setting           | Where                                     |
|-------------------|-------------------------------------------|
| Lidar model       | `LIDAR_MODEL=l2\|l1`: a Docker build arg, also the default of the launch arg `model` |
| Driver parameters | `bot_bringup/config/lidar_<model>.yaml`   |
| Topic/frame names | `lidar.launch.py` (`TOPICS`, `FRAMES`)    |

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
ros/lidar_view.sh            # works over SSH: one sample from each topic, then live rates
xhost +local:                # run in a terminal on the Jetson desktop, once per login
ros/lidar_view.sh --rviz     # opens RViz2 on the attached monitor (:0)
```
