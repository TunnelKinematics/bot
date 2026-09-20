"""Live viewer: python scripts/view.py oak"""
import sys

import cv2
import numpy as np

from bot.sensors.camera import create_camera

with create_camera(sys.argv[1]) as cam:
    print(cam.calibration(), "imu:", cam.has_imu)
    while cv2.waitKey(1) != ord("q"):
        sf = cam.get_stereo()
        depth = np.nan_to_num(sf.depth, nan=0).clip(0, 4) / 4 * 255
        cv2.imshow("stereo", np.hstack([sf.left, sf.right]))
        cv2.imshow("depth", cv2.applyColorMap(depth.astype(np.uint8), cv2.COLORMAP_JET))
        cv2.imshow("rgb", cam.get_rgb().image)
        if imu := cam.get_imu():
            print(f"\rimu {len(imu)} samples, accel {imu[-1].accel.round(2)}", end="")
