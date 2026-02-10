"""Installable component definitions for the interactive dashboard."""

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class InstallableComponent:
    key: str
    name: str
    help_text: str
    deploy_fn: Callable[[], Any] | None = None
    scripts: list[str] = field(default_factory=list)  # Kept for backwards compat
    checks: list[str] = field(default_factory=list)
    has_submenu: bool = False


def _get_rockchip_components() -> list[InstallableComponent]:
    """Lazily import and create Rockchip components to avoid circular imports."""
    from videonode_sbc_config.deploys.generic.cockpit import install_cockpit
    from videonode_sbc_config.deploys.generic.led_permissions import (
        setup_led_permissions,
    )
    from videonode_sbc_config.deploys.hardware.rockchip.permissions import (
        setup_permissions,
    )
    from videonode_sbc_config.deploys.hardware.rockchip.stack import (
        install_rockchip_stack,
    )
    from videonode_sbc_config.deploys.os.armbian.led_disable import disable_leds

    return [
        InstallableComponent(
            key="1",
            name="FFmpeg stack",
            help_text="MPP/RGA hardware encoding",
            deploy_fn=lambda: install_rockchip_stack(_sudo=True),
            checks=["FFmpeg encoders"],
        ),
        InstallableComponent(
            key="2",
            name="Device permissions",
            help_text="MPP/RGA/DMA device access",
            deploy_fn=lambda: setup_permissions(_sudo=True),
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
            deploy_fn=lambda: (
                setup_led_permissions(_sudo=True),
                disable_leds(_sudo=True),
            ),
            checks=["Blue LED", "Green LED"],
        ),
        InstallableComponent(
            key="5",
            name="Cockpit",
            help_text="Web management panel",
            deploy_fn=lambda: install_cockpit(_sudo=True),
            checks=["Cockpit"],
        ),
    ]


def get_components_for_platform(
    is_rockchip: bool, is_armbian: bool
) -> list[InstallableComponent]:
    if is_rockchip and is_armbian:
        return _get_rockchip_components()
    return []
