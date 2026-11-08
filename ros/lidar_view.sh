#!/usr/bin/env bash
set -euo pipefail
topics=(/lidar/points /lidar/imu)

if ! command -v ros2 >/dev/null; then
  exec docker exec -i $([ -t 0 ] && echo -t) bot /entrypoint.sh bash -c "$(<"$0")" "$0" "$@"
fi

case "${1:-}" in
  "") ;;
  --rviz)
    rviz=$(ros2 pkg prefix --share bot_bringup 2>/dev/null)/rviz/lidar.rviz
    [ -f "$rviz" ] || rviz=$(dirname "$0")/src/bot_bringup/rviz/lidar.rviz
    exec rviz2 -d "$rviz" ;;
  *) echo "usage: $0 [--rviz]" >&2; exit 2 ;;
esac

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
