"""
Fix Rockchip MPP/RGA device permissions for hardware encoding/decoding.
Resolves "Failed to init MPP context" errors when using ffmpeg rkmpp encoders.

Usage:
    pyinfra @local deploys/hardware/rockchip/permissions.py
"""

from io import StringIO

from pyinfra.api.deploy import deploy
from pyinfra.context import host
from pyinfra.facts.server import Command
from pyinfra.operations import files, server

UDEV_RULES = """# Rockchip MPP (Media Process Platform)
KERNEL=="mpp_service", MODE="0666", GROUP="video"
KERNEL=="mpp-service", MODE="0666", GROUP="video"
KERNEL=="vpu_service", MODE="0666", GROUP="video"
KERNEL=="vpu-service", MODE="0666", GROUP="video"
KERNEL=="rkvdec", MODE="0666", GROUP="video"
KERNEL=="rkvenc", MODE="0666", GROUP="video"
KERNEL=="vepu", MODE="0666", GROUP="video"
KERNEL=="vdpu", MODE="0666", GROUP="video"

# Rockchip RGA (2D Graphics Acceleration)
KERNEL=="rga", MODE="0666", GROUP="video"

# DMA heap for buffer allocation
SUBSYSTEM=="dma_heap", MODE="0666", GROUP="video"
KERNEL=="system", SUBSYSTEM=="dma_heap", MODE="0666", GROUP="video"
KERNEL=="system-uncached", SUBSYSTEM=="dma_heap", MODE="0666", GROUP="video"
KERNEL=="reserved", SUBSYSTEM=="dma_heap", MODE="0666", GROUP="video"
"""


@deploy("Setup Rockchip permissions")
def setup_permissions() -> None:
    """Configure udev rules and user lingering for Rockchip hardware access."""
    put_rules = files.put(
        name="Setup Rockchip device permissions",
        src=StringIO(UDEV_RULES),
        dest="/etc/udev/rules.d/99-rockchip-permissions.rules",
        mode="644",
    )

    server.shell(
        name="Reload udev rules",
        commands=[
            "udevadm control --reload-rules",
            "udevadm trigger",
        ],
        _if=put_rules.did_change,
    )

    username = host.get_fact(Command, command="whoami").strip()
    server.shell(
        name="Enable lingering for user services to start at boot",
        commands=[f"loginctl enable-linger {username}"],
    )


if __name__ == "__main__":
    setup_permissions(_sudo=True)
