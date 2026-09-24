# Base is multi-arch: arm64 on Apple Silicon / Jetson, amd64 on x86 hosts.
FROM ros:humble

ARG USERNAME=ros
ARG USER_UID=1000
ARG USER_GID=1000

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-pip \
        python3-colcon-common-extensions \
        ros-humble-foxglove-bridge \
        ros-humble-rosbag2-storage-mcap \
        ros-humble-xacro \
        ros-humble-robot-state-publisher \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir mujoco

# Non-root user; -o allows reusing an existing GID.
RUN groupadd -o -g ${USER_GID} ${USERNAME} \
    && useradd -o -m -s /bin/bash -u ${USER_UID} -g ${USER_GID} ${USERNAME} \
    && mkdir -p /ws/src /ws/build /ws/install /ws/log \
    && chown -R ${USER_UID}:${USER_GID} /ws

RUN echo 'source /opt/ros/humble/setup.bash' >> /home/${USERNAME}/.bashrc \
    && echo '[ -f /ws/install/setup.bash ] && source /ws/install/setup.bash' >> /home/${USERNAME}/.bashrc

USER ${USERNAME}
WORKDIR /ws
CMD ["bash"]
