"""
Fix Rockchip MPP/RGA device permissions for hardware encoding/decoding.
Resolves "Failed to init MPP context" errors when using ffmpeg rkmpp encoders.

Usage:
    pyinfra @local deploys/hardware/rockchip/permissions.py
"""

from io import StringIO
from typing import TYPE_CHECKING

from pyinfra.context import host
from pyinfra.facts.server import Command
from pyinfra.operations import files, server

if TYPE_CHECKING:
    pass

# Create comprehensive udev rules for all Rockchip devices
files.put(
    name="Setup Rockchip device permissions",
    src=StringIO("""# Rockchip MPP (Media Process Platform)
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
"""),
    dest="/etc/udev/rules.d/99-rockchip-permissions.rules",
    mode="644",
    _sudo=True,
    _ignore_errors=False,
)

# Reload udev rules
server.shell(
    name="Reload udev rules",
    commands=[
        "udevadm control --reload-rules",
        "udevadm trigger",
    ],
    _sudo=True,
    _ignore_errors=False,
)

# Get the username for lingering setup
USERNAME = host.get_fact(Command, command="whoami").strip()

# Enable lingering so user services start at boot without login
server.shell(
    name="Enable lingering for user services to start at boot",
    commands=[f"loginctl enable-linger {USERNAME}"],
    _sudo=True,
)
