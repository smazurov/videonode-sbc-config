"""
Orchestrator to install complete FFmpeg stack with Rockchip hardware acceleration.

Usage:
    pyinfra @local deploys/hardware/rockchip/stack.py
"""

from pyinfra import local
from pyinfra.operations import python


def install_complete_stack() -> None:
    # Install components in order
    # MPP first (Media Process Platform)
    print("\n[1/3] Installing Rockchip MPP...")
    local.include("deploys/hardware/rockchip/mpp.py")

    # RGA second (2D Graphics Acceleration)
    print("\n[2/3] Installing Rockchip RGA...")
    local.include("deploys/hardware/rockchip/rga.py")

    # FFmpeg last (depends on MPP and RGA)
    print("\n[3/3] Installing FFmpeg with Rockchip support...")
    local.include("deploys/hardware/rockchip/ffmpeg.py")


# Execute the installation
python.call(
    name="Install FFmpeg Rockchip stack",
    function=install_complete_stack,
)
