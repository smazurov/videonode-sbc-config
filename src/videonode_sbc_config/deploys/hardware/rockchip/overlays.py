"""
RK3588 device tree overlay definitions.

This module contains the DTS content for various RK3588 hardware configurations.
The actual application of overlays is OS-specific (see os/armbian/kernel_overlays.py).

To add a new overlay:
1. Add entry to OVERLAYS dict with id, name, description, and dts content
2. Optionally add to DEFAULT_OVERLAYS or BOARD_OVERLAYS
"""

from dataclasses import dataclass


@dataclass
class Overlay:
    id: str
    name: str
    description: str
    dts: str


OVERLAYS: list[Overlay] = [
    Overlay(
        id="usb-host-mode",
        name="USB host mode",
        description="Force USB OTG port to host mode",
        dts="""/dts-v1/;
/plugin/;

/ {
    compatible = "rockchip,rk3588", "rockchip,rk3588s";

    fragment@0 {
        target-path = "/usbdrd3_0/usb@fc000000";
        __overlay__ {
            dr_mode = "host";
            /delete-property/ extcon;
            status = "okay";
        };
    };
};
""",
    ),
    Overlay(
        id="disable-hdmirx",
        name="Disable HDMI RX",
        description="Disable HDMI receiver (stops error spam)",
        dts="""/dts-v1/;
/plugin/;

/ {
    compatible = "rockchip,rk3588", "rockchip,rk3588s";

    fragment@0 {
        target-path = "/hdmirx-controller@fdee0000";
        __overlay__ {
            status = "disabled";
        };
    };
};
""",
    ),
]


def get_overlay(overlay_id: str) -> Overlay | None:
    """Get overlay by ID."""
    for overlay in OVERLAYS:
        if overlay.id == overlay_id:
            return overlay
    return None


def get_overlay_ids() -> list[str]:
    """Get list of all overlay IDs."""
    return [o.id for o in OVERLAYS]
