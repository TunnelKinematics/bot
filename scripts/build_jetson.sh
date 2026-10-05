#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ISAAC_COMMON="$ROOT/.cache/isaac_ros_common"
ISAAC_COMMIT="fcf4d9e17f8f0a7f47f1d22d6a18421ce3768c01"

if [[ "$(uname -m)" != "aarch64" ]]; then
  echo "This image must be built on the Jetson." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Your user cannot access Docker." >&2
  echo "Run: sudo usermod -aG docker \$USER" >&2
  echo "Then: newgrp docker" >&2
  exit 1
fi

if ! docker info --format '{{json .Runtimes}}' | grep -q '"nvidia"'; then
  echo "Docker's NVIDIA runtime is not configured." >&2
  echo "Run: sudo nvidia-ctk runtime configure --runtime=docker" >&2
  echo "Then: sudo systemctl restart docker" >&2
  exit 1
fi

mkdir -p "$ROOT/.cache/zed/resources" "$ROOT/.cache/zed/settings"

if [[ ! -d "$ISAAC_COMMON/.git" ]]; then
  git clone https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_common.git \
    "$ISAAC_COMMON"
fi
git -C "$ISAAC_COMMON" fetch origin "$ISAAC_COMMIT"
git -C "$ISAAC_COMMON" checkout --detach "$ISAAC_COMMIT"

"$ISAAC_COMMON/scripts/build_image_layers.sh" \
  --image_key aarch64.ros2_humble \
  --image_name bot-isaac-base:3.2

docker compose -f "$ROOT/docker/compose.yml" build
