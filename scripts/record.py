"""Record a walk for offline SLAM. Press q in the window to stop.

python scripts/record.py oak recordings/walk1             # left/right/depth
python scripts/record.py oak recordings/walk1 --no-depth

--no-depth records left/right only (depth from a stereo model later).
"""

import sys
from pathlib import Path

import cv2

from bot.sensors.camera import create_camera
from bot.sensors.recorder import record


def show(sf):
    cv2.imshow("left", sf.left)
    return cv2.waitKey(1) == ord("q")


with create_camera(sys.argv[1], depth="--no-depth" not in sys.argv) as cam:
    n = record(cam, Path(sys.argv[2]), show)
print(f"recorded {n} frames to {sys.argv[2]}")
