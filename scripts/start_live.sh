#!/usr/bin/env bash
set -eo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SETUP="$ROOT/ros/install/setup.bash"

if [[ ! -f "$SETUP" ]]; then
  echo "Build the workspace first:" >&2
  echo "  cd $ROOT/ros && colcon build --symlink-install" >&2
  exit 1
fi
source "$SETUP"

HOST_IP="$(tailscale ip -4 2>/dev/null | awk 'NR == 1 {print; exit}')"
if [[ -z "$HOST_IP" ]]; then
  echo "Tailscale is not connected." >&2
  exit 1
fi

python3 -m http.server 8080 \
  --bind 0.0.0.0 \
  --directory "$ROOT/dashboard" \
  >/tmp/bot-dashboard.log 2>&1 &
HTTP_PID=$!

cleanup() {
  kill "$HTTP_PID" 2>/dev/null || true
  wait "$HTTP_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo
echo "Robot dashboard: http://$HOST_IP:8080"
echo "Press Ctrl-C here to stop the robot stack."
echo

ros2 launch bot_bringup live.launch.py "$@"
