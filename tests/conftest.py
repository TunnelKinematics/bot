import pytest


@pytest.fixture(scope="session")
def oak():
    dai = pytest.importorskip("depthai")
    if not dai.Device.getAllAvailableDevices():
        pytest.skip("no OAK device connected")
    from bot.sensors.oak import OakCamera

    with OakCamera() as cam:
        yield cam
