"""Platform type definitions."""

from dataclasses import dataclass
from enum import Enum, auto


class SBCFamily(Enum):
    """SBC hardware family."""

    ROCKCHIP = auto()
    RASPBERRY_PI = auto()
    ALLWINNER = auto()
    UNKNOWN = auto()


class SBCModel(Enum):
    """Specific SBC model."""

    # Rockchip
    RK3588 = auto()
    RK3588S = auto()
    RK3566 = auto()
    RK3576 = auto()
    # Raspberry Pi
    RPI4 = auto()
    RPI5 = auto()
    # Allwinner
    H616 = auto()
    H618 = auto()
    # Fallback
    UNKNOWN = auto()


class OSType(Enum):
    """Operating system type."""

    ARMBIAN = auto()
    DEBIAN = auto()
    UBUNTU = auto()
    DIETPI = auto()
    VENDOR = auto()
    UNKNOWN = auto()


@dataclass(frozen=True)
class Platform:
    """Detected platform information."""

    os_type: OSType
    sbc_family: SBCFamily
    sbc_model: SBCModel
    os_version: str = ""
    kernel_version: str = ""
    board: str = ""  # Armbian BOARD identifier (e.g., "orangepi5ultra")

    @property
    def is_rockchip(self) -> bool:
        return self.sbc_family == SBCFamily.ROCKCHIP

    @property
    def is_armbian(self) -> bool:
        return self.os_type == OSType.ARMBIAN

    @property
    def is_supported(self) -> bool:
        """Check if this platform is currently supported."""
        return self.is_rockchip and self.is_armbian

    def __str__(self) -> str:
        return f"{self.sbc_family.name}/{self.sbc_model.name} on {self.os_type.name}"
