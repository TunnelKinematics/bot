FROM ros:jazzy-ros-base-noble@sha256:8eed0a4669bbf43ee331878a4c39bd8ebddea8e3312a58b4fae8edb14526b617

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpcl-dev \
        ros-jazzy-pcl-conversions \
    && rm -rf /var/lib/apt/lists/*

# The driver's CMakeLists finds the prebuilt SDK by a path relative to the repo root.
RUN git init -q /tmp/sdk \
    && git -C /tmp/sdk fetch -q --depth 1 https://github.com/unitreerobotics/unilidar_sdk2 0e3c51f512e6b8ff60b8c32f160b412cb48445c2 \
    && git -C /tmp/sdk checkout -q FETCH_HEAD \
    && . /opt/ros/jazzy/setup.sh \
    && colcon --log-base /dev/null build --merge-install \
        --base-paths /tmp/sdk/unitree_lidar_ros2 --build-base /tmp/build --install-base /opt/unilidar \
        --cmake-args -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=17 \
    && rm -rf /tmp/sdk /tmp/build

RUN apt-get update && apt-get install -y --no-install-recommends \
        ros-jazzy-foxglove-bridge \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-dev \
        ros-jazzy-pcl-ros \
    && rm -rf /var/lib/apt/lists/* \
    && git init -q /tmp/slam \
    && git -C /tmp/slam fetch -q --depth 1 https://github.com/dfloreaa/point_lio_ros2 a8e2d0d5090af97ead8dd4fac3d37cf3dbb33ff7 \
    && git -C /tmp/slam checkout -q FETCH_HEAD \
    && . /opt/ros/jazzy/setup.sh \
    && colcon --log-base /dev/null build --merge-install \
        --base-paths /tmp/slam --build-base /tmp/build --install-base /opt/slam \
        --cmake-args -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=17 \
    && rm -rf /tmp/slam /tmp/build

RUN apt-get update && apt-get install -y --no-install-recommends \
        ros-jazzy-robot-state-publisher \
        ros-jazzy-xacro \
    && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /entrypoint.sh
RUN echo '. /entrypoint.sh' >> /root/.bashrc
WORKDIR /ws
ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
