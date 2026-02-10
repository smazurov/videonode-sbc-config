"""
Install Rockchip RGA (2D Graphics Acceleration) using pyinfra.

Usage:
    pyinfra @local deploys/hardware/rockchip/rga.py
    pyinfra @local deploys/hardware/rockchip/rga.py --data rebuild=true
"""

from pyinfra.api.deploy import deploy
from pyinfra.context import host
from pyinfra.facts.server import Home
from pyinfra.operations import apt, files, server

from videonode_sbc_config.deploys.utils import get_build_dependencies

RGA_BRANCH = "jellyfin-rga"
RGA_REPO = "https://github.com/nyanmisaka/rk-mirrors.git"


@deploy("Install Rockchip RGA")
def install_rga(rebuild: bool = False) -> None:
    """Install Rockchip 2D Graphics Acceleration libraries."""
    user_home = host.get_fact(Home)
    build_base = f"{user_home}/dev"
    build_dir = f"{build_base}/rkrga"
    build_path = f"{build_dir}/build"

    deps = apt.packages(
        name="Install RGA build dependencies",
        packages=get_build_dependencies("base", "rga"),
        update=True,
    )

    files.directory(
        name="Create RGA build directory",
        path=build_base,
        _if=deps.did_succeed,
    )

    files.directory(
        name="Remove existing RGA directory if present",
        path=build_dir,
        present=False,
        _if=deps.did_succeed,
    )

    clone = server.shell(
        name="Clone Rockchip RGA repository",
        commands=[f"git clone --depth 1 --branch {RGA_BRANCH} {RGA_REPO} {build_dir}"],
        _if=deps.did_succeed,
        _retries=2,  # type: ignore[call-arg]
        _retry_delay=5,  # type: ignore[call-arg]
    )

    configure = server.shell(
        name="Configure RGA with meson",
        commands=[
            f"cd {build_dir} && meson setup build --prefix=/usr --libdir=lib --buildtype=release --default-library=shared -Dcpp_args=-fpermissive -Dlibdrm=false -Dlibrga_demo=false"
        ],
        _if=clone.did_succeed,
    )

    server.shell(
        name="Build and install RGA libraries",
        commands=[
            f"cd {build_path} && ninja",
            f"cd {build_path} && ninja install",
            "ldconfig",
        ],
        _if=configure.did_succeed,
    )


if __name__ == "__main__":
    rebuild = bool(host.data.get("rebuild", False))
    install_rga(rebuild=rebuild, _sudo=True)
