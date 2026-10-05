ARG BASE_IMAGE=bot-isaac-base:3.2
FROM ${BASE_IMAGE}

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive

ARG ZED_SDK_VERSION=5.3.1
ARG ZED_WRAPPER_VERSION=v5.3.1

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpng-dev \
        libusb-1.0-0-dev \
        ros-humble-isaac-ros-nvblox \
        ros-humble-isaac-ros-visual-slam \
        ros-humble-rosbridge-server \
        ros-humble-web-video-server \
        zstd \
    && rm -rf /var/lib/apt/lists/*

# Isaac ROS 3.2's generated CMake targets reference this exact NumPy header path.
RUN python3 -m pip install --no-cache-dir --force-reinstall "numpy==1.26.4" \
    && NUMPY_INCLUDE="$(python3 -c 'import numpy; print(numpy.get_include())')" \
    && EXPECTED="/usr/local/lib/python3.10/dist-packages/numpy/core/include" \
    && if [[ "$NUMPY_INCLUDE" != "$EXPECTED" ]]; then \
         mkdir -p "$(dirname "$EXPECTED")"; \
         ln -sfn "$NUMPY_INCLUDE" "$EXPECTED"; \
       fi \
    && test -d "$EXPECTED"

# ZED SDK for JetPack 6 / L4T 36.4. CUDA is supplied by the Isaac ROS base.
RUN wget -q -O /tmp/zed.run \
        "https://download.stereolabs.com/zedsdk/${ZED_SDK_VERSION}/l4t36.4/jetsons" \
    && chmod +x /tmp/zed.run \
    && /tmp/zed.run -- silent skip_tools skip_cuda \
    && rm /tmp/zed.run

# Pin the wrapper to the SDK release instead of building a moving branch.
RUN git clone --depth 1 --branch "${ZED_WRAPPER_VERSION}" --recurse-submodules \
        https://github.com/stereolabs/zed-ros2-wrapper.git /opt/zed_ws/src/zed-ros2-wrapper \
    && source /opt/ros/humble/setup.bash \
    && rosdep update \
    && rosdep install \
        --from-paths /opt/zed_ws/src \
        --ignore-src \
        --rosdistro humble \
        -r -y \
    && NUMPY_INCLUDE="$(python3 -c 'import numpy; print(numpy.get_include())')" \
    && EXPECTED="/usr/local/lib/python3.10/dist-packages/numpy/core/include" \
    && if [[ "$NUMPY_INCLUDE" != "$EXPECTED" ]]; then \
         rm -rf "$EXPECTED"; \
         mkdir -p "$(dirname "$EXPECTED")"; \
         ln -s "$NUMPY_INCLUDE" "$EXPECTED"; \
       fi \
    && test -d "$EXPECTED" \
    && cd /opt/zed_ws \
    && colcon build \
        --merge-install \
        --cmake-args -DCMAKE_BUILD_TYPE=Release \
        --packages-up-to zed_wrapper \
    && rm -rf build log /var/lib/apt/lists/*

# The ZED NITROS component loads this GXF extension at runtime.
RUN rm -f /etc/apt/sources.list.d/yarn.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ros-humble-gxf-isaac-optimizer \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
CMD ["/workspace/scripts/run_live.sh"]
