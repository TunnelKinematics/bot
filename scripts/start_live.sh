#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

HOST_IP="$(tailscale ip -4 2>/dev/null | awk 'NR == 1 {print; exit}')"
if [[ -z "$HOST_IP" ]]; then
  echo "Tailscale is not connected." >&2
  exit 1
fi

if ! docker image inspect bot-ros:humble >/dev/null 2>&1; then
  "$ROOT/scripts/build_jetson.sh"
fi

echo
echo "Robot dashboard: http://$HOST_IP:8080"
echo "Press Ctrl-C here to stop the robot stack."
echo

docker compose -f "$ROOT/docker/compose.yml" up
