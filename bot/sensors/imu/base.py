from abc import ABC, abstractmethod

from .types import ImuSample


class ImuSource(ABC):
    @abstractmethod
    def get_imu(self) -> list[ImuSample]:
        """All samples since the last call, oldest first."""
