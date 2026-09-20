"""Dense mapping with NVIDIA nvblox.

https://github.com/nvidia-isaac/nvblox (nvblox_torch wheel) - GPU only.
"""

from dataclasses import dataclass

import numpy as np
import torch
from nvblox_torch.constants import constants
from nvblox_torch.mapper import Mapper, QueryType
from nvblox_torch.mapper_params import MapperParams, ProjectiveIntegratorParams
from nvblox_torch.sensor import Sensor

from ..common.types import T_BODY_OPTICAL, Pose
from ..sensors.types import StereoCalibration, StereoFrame


@dataclass(frozen=True)
class OccupancyGrid:
    cells: (
        np.ndarray
    )  # int8, nav_msgs convention: -1 unknown, 0 free, 100 occupied
    resolution: float  # meters per cell
    origin: np.ndarray  # world xy of cells[0, 0]


class NvbloxMapper:
    """Fuses depth from every stereo pair of the rig into one TSDF; mesh
    and ESDF-derived occupancy out."""

    def __init__(
        self,
        calibs: list[StereoCalibration],
        voxel: float = 0.02,
        max_depth: float = 3.0,
        grid_resolution: float = 0.05,
        z_band: tuple[float, float] = (-0.15, 1.0),
    ):
        self.calibs = calibs
        self.sensors = [
            Sensor.from_camera(
                fu=c.intrinsics.fx,
                fv=c.intrinsics.fy,
                cu=c.intrinsics.cx,
                cv=c.intrinsics.cy,
                width=c.intrinsics.width,
                height=c.intrinsics.height,
            )
            for c in calibs
        ]
        self.grid_resolution, self.z_band = grid_resolution, z_band
        integrator = ProjectiveIntegratorParams()
        integrator.projective_integrator_max_integration_distance_m = max_depth
        params = MapperParams()
        params.set_projective_integrator_params(integrator)
        self.mapper = Mapper(voxel_sizes_m=voxel, mapper_parameters=params)
        self.max_depth = max_depth
        self.bounds = np.array(
            [[np.inf] * 3, [-np.inf] * 3]
        )  # world xyz reachable by any integrated frame, for the grid extent

    def integrate(self, frames: list[StereoFrame], pose: Pose) -> None:
        """One frame per stereo pair, in rig order; pose is the body pose
        of the rig."""
        for sf, calib, sensor in zip(
            frames, self.calibs, self.sensors, strict=False
        ):
            if sf.depth is None:
                continue
            T_world_optical = pose.matrix @ T_BODY_OPTICAL @ calib.left_to_rig
            t_w_c = torch.from_numpy(T_world_optical.astype(np.float32))
            depth = torch.from_numpy(
                np.nan_to_num(sf.depth)
            ).cuda()  # 0 = invalid for nvblox
            self.mapper.add_depth_frame(depth, t_w_c, sensor)
            gray = np.repeat(sf.left[..., None], 3, -1)  # mono -> RGB texture
            self.mapper.add_color_frame(
                torch.from_numpy(np.ascontiguousarray(gray)).cuda(),
                t_w_c,
                sensor,
            )
            t = T_world_optical[:3, 3]
            self.bounds = np.array(
                [
                    np.minimum(self.bounds[0], t - self.max_depth),
                    np.maximum(self.bounds[1], t + self.max_depth),
                ]
            )

    def save_mesh(self, path: str) -> int:
        """Writes the surface mesh (.ply); returns the vertex count."""
        self.mapper.update_color_mesh()
        mesh = self.mapper.get_color_mesh()
        mesh.save(path)
        return len(mesh.vertices())

    def occupancy(self) -> OccupancyGrid:
        """2D grid from the ESDF: a cell is occupied if any voxel in z_band
        is within one cell of a surface."""
        self.mapper.update_esdf()
        res, (lo, hi) = self.grid_resolution, self.z_band
        origin = (
            np.floor(np.minimum(self.bounds[0, :2], 0) / res) * res
        )  # always cover the world origin
        n = (
            np.ceil((np.maximum(self.bounds[1, :2], 0) - origin) / res).astype(
                int
            )
            + 1
        )
        ys, xs = np.mgrid[0 : n[1], 0 : n[0]]
        xy = np.stack([xs, ys], -1).reshape(-1, 2) * res + origin + res / 2
        cells = np.full(n[1] * n[0], -1, np.int8)
        for z in np.arange(lo, hi, res):
            zr = np.full((len(xy), 2), z, np.float32)
            zr[:, 1] = 0  # ESDF queries are spheres: xyz + radius
            pts = torch.from_numpy(
                np.hstack([xy, zr]).astype(np.float32)
            ).cuda()
            d = (
                self.mapper.query_layer(QueryType.ESDF, pts)[:, 0]
                .cpu()
                .numpy()
            )
            known = d != constants.esdf_unknown_distance()
            cells[known & (cells != 100)] = 0
            cells[known & (d < res)] = 100
        return OccupancyGrid(cells.reshape(n[1], n[0]), res, origin)
