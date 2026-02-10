"""
Install the complete Rockchip video stack (MPP, RGA, FFmpeg) using pyinfra.

Usage:
    pyinfra @local deploys/hardware/rockchip/stack.py
    pyinfra @local deploys/hardware/rockchip/stack.py --data rebuild=true
"""

from pyinfra.api.deploy import deploy
from pyinfra.context import host

from .ffmpeg import install_ffmpeg
from .mpp import install_mpp
from .permissions import setup_permissions
from .rga import install_rga


@deploy("Install Rockchip Video Stack")
def install_rockchip_stack(rebuild: bool = False) -> None:
    """Install the complete Rockchip video stack with hardware acceleration."""
    setup_permissions()
    mpp = install_mpp(rebuild=rebuild)
    rga = install_rga(rebuild=rebuild, _if=mpp.did_succeed)
    install_ffmpeg(rebuild=rebuild, _if=rga.did_succeed)


if __name__ == "__main__":
    rebuild = bool(host.data.get("rebuild", False))
    install_rockchip_stack(rebuild=rebuild, _sudo=True)
