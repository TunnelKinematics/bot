import csv
import json
from dataclasses import asdict
from pathlib import Path

import cv2
import numpy as np

from .camera import StereoCamera

FAST_PNG = [
    cv2.IMWRITE_PNG_COMPRESSION,
    1,
]  # default level 3 can't keep up with 30 fps x 3 streams


def record(cam: StereoCamera, out: Path, should_stop) -> int:
    """Writes left/right/depth PNGs (depth uint16 mm), frames.csv, imu.csv
    and calibration.json until should_stop(frame)."""
    for d in ("left", "right", "depth"):
        (out / d).mkdir(parents=True, exist_ok=True)
    (out / "calibration.json").write_text(
        json.dumps(asdict(cam.calibration()), default=lambda a: a.tolist())
    )
    with open(out / "frames.csv", "w") as ff, open(out / "imu.csv", "w") as fi:
        frames, imu = csv.writer(ff), csv.writer(fi)
        frames.writerow(["index", "timestamp"])
        imu.writerow(["timestamp", "ax", "ay", "az", "gx", "gy", "gz"])
        i = 0
        while not should_stop(sf := cam.get_stereo()):
            cv2.imwrite(str(out / f"left/{i:06d}.png"), sf.left, FAST_PNG)
            cv2.imwrite(str(out / f"right/{i:06d}.png"), sf.right, FAST_PNG)
            if sf.depth is not None:
                cv2.imwrite(
                    str(out / f"depth/{i:06d}.png"),
                    (np.nan_to_num(sf.depth) * 1000).astype(np.uint16),
                    FAST_PNG,
                )
            frames.writerow([i, f"{sf.timestamp:.6f}"])
            imu.writerows(
                [
                    [f"{s.timestamp:.6f}", *s.accel, *s.gyro]
                    for s in cam.get_imu()
                ]
            )
            i += 1
    return i
