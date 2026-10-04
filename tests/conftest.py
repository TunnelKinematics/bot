import pytest


@pytest.fixture(scope="session")
def zed():
    pytest.importorskip("pyzed.sl")
    from bot.sensors.zed import ZedCamera

    cam = ZedCamera()
    try:
        cam.open()
    except RuntimeError as exc:
        pytest.skip(str(exc))
    try:
        yield cam
    finally:
        cam.close()
