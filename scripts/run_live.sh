#!/usr/bin/env bash
set -eo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

source /opt/ros/humble/setup.bash
source /opt/zed_ws/install/setup.bash

cd "$ROOT/ros"
colcon build --symlink-install
source install/setup.bash

python3 "$ROOT/scripts/serve_dashboard.py" 8080 "$ROOT/dashboard" \
  >/tmp/bot-dashboard.log 2>&1 &
HTTP_PID=$!

cleanup() {
  kill "$HTTP_PID" 2>/dev/null || true
  wait "$HTTP_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

ros2 launch bot_bringup live.launch.py "$@"
