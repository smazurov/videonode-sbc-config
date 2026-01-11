"""Installable component definitions for the interactive dashboard."""

from dataclasses import dataclass, field


@dataclass
class InstallableComponent:
    key: str
    name: str
    help_text: str
    scripts: list[str] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)
    has_submenu: bool = False


ROCKCHIP_ARMBIAN_COMPONENTS: list[InstallableComponent] = [
    InstallableComponent(
        key="1",
        name="FFmpeg stack",
        help_text="MPP/RGA hardware encoding",
        scripts=[
            "hardware/rockchip/mpp.py",
            "hardware/rockchip/rga.py",
            "hardware/rockchip/ffmpeg.py",
        ],
        checks=["FFmpeg encoders"],
    ),
    InstallableComponent(
        key="2",
        name="Device permissions",
        help_text="MPP/RGA/DMA device access",
        scripts=["hardware/rockchip/permissions.py"],
        checks=["MPP permissions", "RGA permissions", "DMA heap permissions"],
    ),
    InstallableComponent(
        key="3",
        name="Kernel overlays",
        help_text="Device tree overlays",
        has_submenu=True,
    ),
    InstallableComponent(
        key="4",
        name="LED control",
        help_text="Disable status LEDs",
        scripts=[
            "generic/led_permissions.py",
            "os/armbian/led_disable.py",
        ],
        checks=["Blue LED", "Green LED"],
    ),
    InstallableComponent(
        key="5",
        name="Cockpit",
        help_text="Web management panel",
        scripts=["generic/cockpit.py"],
        checks=["Cockpit"],
    ),
]


def get_components_for_platform(
    is_rockchip: bool, is_armbian: bool
) -> list[InstallableComponent]:
    if is_rockchip and is_armbian:
        return ROCKCHIP_ARMBIAN_COMPONENTS
    return []
