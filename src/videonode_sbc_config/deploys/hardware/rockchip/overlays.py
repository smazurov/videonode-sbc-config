"""
RK3588 device tree overlay definitions.

This module contains the DTS content for various RK3588 hardware configurations.
The actual application of overlays is OS-specific (see os/armbian/kernel_overlays.py).
"""

# USB OTG port in host mode overlay
USB_HOST_MODE_DTS = """/dts-v1/;
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
"""

# Disable HDMI receiver overlay (stops error spam)
DISABLE_HDMIRX_DTS = """/dts-v1/;
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
"""

# Map of overlay name -> DTS content
OVERLAYS: dict[str, str] = {
    "usb-host-mode": USB_HOST_MODE_DTS,
    "disable-hdmirx": DISABLE_HDMIRX_DTS,
}

# Base overlays applied to all RK3588 boards
BASE_OVERLAYS: list[str] = ["disable-hdmirx"]

# Board-specific overlays (exact match on Armbian BOARD identifier)
BOARD_OVERLAYS: dict[str, list[str]] = {
    "orangepi5ultra": ["usb-host-mode"],
}


def get_overlays_for_board(board: str) -> list[str]:
    """Get overlay list for a specific board."""
    overlays = list(BASE_OVERLAYS)
    if board in BOARD_OVERLAYS:
        overlays.extend(BOARD_OVERLAYS[board])
    return overlays
