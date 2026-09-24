# Base is multi-arch: arm64 on Apple Silicon / Jetson, amd64 on x86 hosts.
FROM ros:jazzy

ARG USERNAME=ros
ARG USER_UID=1000
ARG USER_GID=1000

ENV DEBIAN_FRONTEND=noninteractive

# EGL + Mesa: headless MuJoCo rendering (MUJOCO_GL=egl) for recording videos.
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-pip \
        python3-colcon-common-extensions \
        ros-jazzy-foxglove-bridge \
        ros-jazzy-rosbag2-storage-mcap \
        ros-jazzy-xacro \
        ros-jazzy-robot-state-publisher \
        libegl1 libegl-mesa0 libgl1 libopengl0 libgl1-mesa-dri \
    && rm -rf /var/lib/apt/lists/*

# Ubuntu 24.04 marks system Python as externally managed (PEP 668).
RUN pip3 install --no-cache-dir --break-system-packages mujoco

# Non-root user; the base image's 'ubuntu' user holds UID 1000, so drop it first.
# -o allows reusing an existing GID.
RUN userdel -r ubuntu \
    && groupadd -o -g ${USER_GID} ${USERNAME} \
    && useradd -o -m -s /bin/bash -u ${USER_UID} -g ${USER_GID} ${USERNAME} \
    && mkdir -p /ws/src /ws/build /ws/install /ws/log \
    && chown -R ${USER_UID}:${USER_GID} /ws

RUN echo 'source /opt/ros/jazzy/setup.bash' >> /home/${USERNAME}/.bashrc \
    && echo '[ -f /ws/install/setup.bash ] && source /ws/install/setup.bash' >> /home/${USERNAME}/.bashrc

USER ${USERNAME}
WORKDIR /ws
CMD ["bash"]
