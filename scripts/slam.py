"""cuVSLAM + nvblox map, live or from recordings. One source per stereo pair
of the rig, in rig order. Press q to stop. Saves trajectory.csv, mesh.ply and
map.png to --out. --optimize (replay only) uses the loop-closed poses and
rebuilds the map.

    python scripts/slam.py oak --out out/live
    python scripts/slam.py recordings/walk1 --out out/walk1 \\
        --optimize --no-show
"""

import argparse
import time
from collections import defaultdict
from contextlib import ExitStack
from pathlib import Path

import cv2
import numpy as np

from bot.perception.cuvslam import Cuvslam
from bot.perception.nvblox import NvbloxMapper
from bot.sensors.camera import create_camera


def grid_image(grid, traj):
    g = grid.occupancy()
    img = cv2.cvtColor(
        np.where(g.cells == 100, 0, np.where(g.cells == 0, 255, 128)).astype(
            np.uint8
        ),
        cv2.COLOR_GRAY2BGR,
    )
    px = ((np.array(traj)[:, 1:3] - g.origin) / g.resolution).astype(np.int32)
    cv2.polylines(img, [px], False, (0, 0, 255), 1)
    cv2.circle(img, tuple(px[0]), 3, (0, 255, 0), -1)
    return img[::-1]


class Timer:
    """Accumulates wall time per stage: with timer("stage"): ..."""

    def __init__(self):
        self.total, self.calls = defaultdict(float), defaultdict(int)

    def __call__(self, stage):
        self.stage = stage
        return self

    def __enter__(self):
        self.t0 = time.perf_counter()

    def __exit__(self, *_):
        self.total[self.stage] += time.perf_counter() - self.t0
        self.calls[self.stage] += 1

    def report(self):
        for stage, t in self.total.items():
            n = self.calls[stage]
            print(f"  {stage:12s} {t:6.1f} s  ({1000 * t / n:.1f} ms x {n})")


ap = argparse.ArgumentParser()
ap.add_argument(
    "sources",
    nargs="+",
    help="oak, or recording directories; one per stereo pair",
)
ap.add_argument("--out", type=Path)
ap.add_argument(
    "--optimize",
    action="store_true",
    help="loop closure + gravity alignment, then rebuild the map "
    "(replay only)",
)
ap.add_argument(
    "--no-show",
    action="store_true",
    help="headless: stop only at end of recording / Ctrl-C",
)
args = ap.parse_args()

traj, keyframes, timer = [], [], Timer()
with ExitStack() as stack:
    cams = [
        stack.enter_context(
            create_camera("replay", path=s)
            if Path(s).is_dir()
            else create_camera(s)
        )
        for s in args.sources
    ]
    calibs = [c.calibration() for c in cams]
    slam, mapper = Cuvslam(calibs), NvbloxMapper(calibs)
    try:
        while args.no_show or cv2.waitKey(1) != ord("q"):
            with timer("read"):
                frames = [c.get_stereo() for c in cams]
            with timer("cuvslam"):
                pose = slam.track(frames, cams[0].get_imu())
            if slam.is_keyframe:
                with timer("nvblox"):
                    mapper.integrate(frames, pose)
                keyframes.append(frames)
            traj.append(
                [
                    pose.timestamp,
                    *pose.position,
                    *pose.orientation,
                    slam.tracked,
                ]
            )
            if not args.no_show:
                cv2.imshow("left", frames[0].left)
            status = "" if slam.tracked else "LOST"
            if not slam.initialized:
                status = "waiting for gravity"
            print(
                f"\rframe {len(traj)}  keyframes {len(keyframes)}  "
                f"pos {pose.position.round(2)}  {status}",
                end="",
            )
    except (KeyboardInterrupt, EOFError):
        pass

    if args.optimize:
        print(f"\noptimizing {len(keyframes)} keyframes...")
        with timer("optimize"):
            poses = slam.optimize()
        mapper = NvbloxMapper(calibs)
        with timer("reintegrate"):
            for frames, pose in zip(keyframes, poses, strict=False):
                mapper.integrate(frames, pose)
        traj = [
            [p.timestamp, *p.position, *p.orientation, True] for p in poses
        ]

traj = np.array(traj)
print(
    f"\n{len(traj)} poses, {(traj[:, -1] > 0).mean():.0%} tracked, "
    f"{len(keyframes)} keyframes"
)
if args.out is None:
    raise SystemExit
args.out.mkdir(parents=True, exist_ok=True)
np.savetxt(
    args.out / "trajectory.csv",
    traj,
    delimiter=",",
    header="t,x,y,z,qx,qy,qz,qw,tracked",
    comments="",
    fmt="%.6f",
)
with timer("occupancy"):
    cv2.imwrite(str(args.out / "map.png"), grid_image(mapper, traj))
with timer("mesh"):
    n_vertices = mapper.save_mesh(str(args.out / "mesh.ply"))
print(f"saved mesh with {n_vertices} vertices -> {args.out}/")
timer.report()
