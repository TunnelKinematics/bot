"""All Modal (cloud GPU) functions: a stand-in for the Jetson, since cuVSLAM
and nvblox need CUDA + Ubuntu. Delete once everything runs on-robot.

    uv run --with modal modal run modal_app.py::slam \
        --recording recordings/walk1 --out out/walk1

A recording is uploaded once as a tarball to the `tv-bot-recordings` volume
(cached by directory name); results are downloaded into --out.
"""

import os
import subprocess
import tarfile
import tempfile
from pathlib import Path

import modal

CUVSLAM = "https://github.com/nvidia-isaac/cuVSLAM/releases/download/v17.0.0/cuvslam-17.0.0%2Bcu12-cp312-abi3-manylinux_2_39_x86_64.whl"
NVBLOX = "https://github.com/nvidia-isaac/nvblox/releases/download/v0.0.10/nvblox_torch-0.0.10%2Bcu12ubuntu24-py3-none-linux_x86_64.whl"
REPO, DATA = "/root/tv-bot", "/data"

image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.8.1-runtime-ubuntu24.04", add_python="3.12"
    )
    .apt_install(
        "libgl1",
        "libegl1",
        "libgomp1",
        "libx11-6",
        "libglib2.0-0",
        "libusb-1.0-0",
    )
    .pip_install(
        "numpy", "scipy", "opencv-python-headless", "torch", CUVSLAM, NVBLOX
    )
    .add_local_dir("bot", remote_path=f"{REPO}/bot")
    .add_local_dir("scripts", remote_path=f"{REPO}/scripts")
)
app = modal.App("tv-bot", image=image)
recordings = modal.Volume.from_name(
    "tv-bot-recordings", create_if_missing=True
)


def upload(recording: Path) -> str:
    """Tar + upload a recording directory to the volume unless already
    there; returns its name."""
    if f"{recording.name}.tar" not in [
        e.path for e in recordings.listdir("/")
    ]:
        with tempfile.TemporaryDirectory() as tmp:
            tar_path = Path(tmp) / f"{recording.name}.tar"
            with tarfile.open(tar_path, "w") as tar:
                tar.add(recording, arcname=recording.name)
            print(
                f"uploading {tar_path.name} "
                f"({tar_path.stat().st_size / 1e6:.0f} MB)...",
                flush=True,
            )
            with recordings.batch_upload() as b:
                b.put_file(str(tar_path), f"/{recording.name}.tar")
    return recording.name


def download(files: dict[str, bytes], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (out / name).write_bytes(data)
    print(f"saved {sorted(files)} -> {out}/")


def extract(name: str) -> Path:
    """Recording from the volume onto local disk: one sequential read, the
    volume is slow per file."""
    with tarfile.open(f"{DATA}/{name}.tar") as tar:
        tar.extractall("/tmp")
    return Path("/tmp") / name


@app.function(gpu="T4", timeout=3600, volumes={DATA: recordings})
def run_slam(name: str, calibration: str, optimize: bool) -> dict[str, bytes]:
    """scripts/slam.py on a recording: cuVSLAM + nvblox, returns
    trajectory.csv / mesh.ply / map.png. calibration.json is sent with every
    call so the cached tar never goes stale when it is edited."""
    rec, out = extract(name), Path("/tmp/out")
    (rec / "calibration.json").write_text(calibration)
    cmd = [
        "python",
        "scripts/slam.py",
        str(rec),
        "--out",
        str(out),
        "--no-show",
    ] + (["--optimize"] if optimize else [])
    subprocess.run(
        cmd, cwd=REPO, check=True, env={**os.environ, "PYTHONPATH": REPO}
    )
    return {f.name: f.read_bytes() for f in out.iterdir()}


@app.local_entrypoint()
def slam(recording: str, out: str, optimize: bool = True):
    rec = Path(recording)
    calibration = (rec / "calibration.json").read_text()
    download(run_slam.remote(upload(rec), calibration, optimize), Path(out))
