#!/usr/bin/env bash
set -euo pipefail
topics=(/lidar/points /lidar/imu)

foxglove_url() {
  local name
  name=$(tailscale status --json 2>/dev/null \
    | python3 -c 'import json, sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))' 2>/dev/null) \
    && [ -n "$name" ] && { echo "wss://$name"; return; }
  echo "ws://$(tailscale ip -4 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}'):8765"
}

[ -f /.dockerenv ] || echo "Foxglove: $(foxglove_url)"

if ! command -v ros2 >/dev/null; then
  exec docker exec "-i$([ -t 0 ] && echo t)" bot /entrypoint.sh bash -c "$(<"$0")" "$0" "$@"
fi

grep -qx /slam/odom <(ros2 topic list) && topics+=(/slam/odom)
for topic in "${topics[@]}"; do
  echo "--- $topic"
  timeout 5 ros2 topic echo --once --no-arr "$topic" || echo "no message on $topic within 5 s" >&2
done

export PYTHONUNBUFFERED=1
trap 'trap - TERM; kill 0' INT TERM
for topic in "${topics[@]}"; do
  ros2 topic hz "$topic" | sed -u "s|^|$topic  |" &
done
wait
