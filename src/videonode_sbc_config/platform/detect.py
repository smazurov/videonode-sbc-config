"""Platform detection logic."""

from pathlib import Path

from .types import OSType, Platform, SBCFamily, SBCModel


def _read_file(path: str) -> str | None:
    """Read file contents, return None if not found."""
    try:
        return Path(path).read_text().strip()
    except (FileNotFoundError, PermissionError):
        return None


def _detect_os() -> tuple[OSType, str, str]:
    """Detect OS type, version, and board identifier."""
    # Check for Armbian first (it's based on Debian/Ubuntu)
    if Path("/etc/armbian-release").exists():
        version = ""
        board = ""
        content = _read_file("/etc/armbian-release")
        if content:
            for line in content.splitlines():
                if line.startswith("VERSION="):
                    version = line.split("=", 1)[1].strip()
                elif line.startswith("BOARD="):
                    board = line.split("=", 1)[1].strip()
        return OSType.ARMBIAN, version, board

    # Check for DietPi
    if Path("/boot/dietpi.txt").exists():
        return OSType.DIETPI, "", ""

    # Fall back to /etc/os-release
    os_release = _read_file("/etc/os-release")
    if os_release:
        os_id = ""
        for line in os_release.splitlines():
            if line.startswith("ID="):
                os_id = line.split("=", 1)[1].strip().strip('"').lower()
                break

        os_map = {"debian": OSType.DEBIAN, "ubuntu": OSType.UBUNTU}
        return os_map.get(os_id, OSType.UNKNOWN), "", ""

    return OSType.UNKNOWN, "", ""


def _detect_sbc() -> tuple[SBCFamily, SBCModel]:
    """Detect SBC family and model from device tree."""
    compatible = _read_file("/proc/device-tree/compatible")
    if not compatible:
        return SBCFamily.UNKNOWN, SBCModel.UNKNOWN

    # Device tree compatible strings are null-separated
    compatible = compatible.replace("\x00", "\n").lower()

    # Rockchip detection
    if "rockchip" in compatible:
        family = SBCFamily.ROCKCHIP
        if "rk3588s" in compatible:
            return family, SBCModel.RK3588S
        if "rk3588" in compatible:
            return family, SBCModel.RK3588
        if "rk3576" in compatible:
            return family, SBCModel.RK3576
        if "rk3566" in compatible:
            return family, SBCModel.RK3566
        return family, SBCModel.UNKNOWN

    # Raspberry Pi detection
    model = _read_file("/proc/device-tree/model") or ""
    model = model.replace("\x00", "").lower()
    if "raspberry" in model or "bcm2" in compatible:
        family = SBCFamily.RASPBERRY_PI
        if "pi 5" in model:
            return family, SBCModel.RPI5
        if "pi 4" in model:
            return family, SBCModel.RPI4
        return family, SBCModel.UNKNOWN

    # Allwinner detection
    if "allwinner" in compatible or "sun" in compatible:
        family = SBCFamily.ALLWINNER
        if "h618" in compatible:
            return family, SBCModel.H618
        if "h616" in compatible:
            return family, SBCModel.H616
        return family, SBCModel.UNKNOWN

    return SBCFamily.UNKNOWN, SBCModel.UNKNOWN


def detect_platform() -> Platform:
    """Detect full platform information."""
    os_type, os_version, board = _detect_os()
    sbc_family, sbc_model = _detect_sbc()

    kernel = _read_file("/proc/version")
    kernel_version = ""
    if kernel:
        parts = kernel.split()
        if len(parts) >= 3:
            kernel_version = parts[2]

    return Platform(
        os_type=os_type,
        sbc_family=sbc_family,
        sbc_model=sbc_model,
        os_version=os_version,
        kernel_version=kernel_version,
        board=board,
    )
