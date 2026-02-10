"""
Install Rockchip MPP (Media Process Platform) using pyinfra.

Usage:
    pyinfra @local deploys/hardware/rockchip/mpp.py
    pyinfra @local deploys/hardware/rockchip/mpp.py --data rebuild=true
"""

from pyinfra.api.deploy import deploy
from pyinfra.context import host
from pyinfra.facts.server import Home
from pyinfra.operations import apt, files, server

from videonode_sbc_config.deploys.utils import get_build_dependencies, get_parallel_jobs

MPP_VERSION = "1.0.10"
MPP_REPO = "https://github.com/HermanChen/mpp.git"


@deploy("Install Rockchip MPP")
def install_mpp(rebuild: bool = False) -> None:
    """Install Rockchip Media Process Platform libraries."""
    user_home = host.get_fact(Home)
    build_base = f"{user_home}/dev"
    build_dir = f"{build_base}/rkmpp"
    build_path = f"{build_dir}/build"
    parallel_jobs = get_parallel_jobs()

    deps = apt.packages(
        name="Install MPP build dependencies",
        packages=get_build_dependencies("base", "mpp"),
        update=True,
    )

    files.directory(
        name="Create MPP build directory",
        path=build_base,
        _if=deps.did_succeed,
    )

    files.directory(
        name="Remove existing MPP directory if present",
        path=build_dir,
        present=False,
        _if=deps.did_succeed,
    )

    clone = server.shell(
        name="Clone Rockchip MPP repository",
        commands=[f"git clone --depth 1 --branch {MPP_VERSION} {MPP_REPO} {build_dir}"],
        _if=deps.did_succeed,
        _retries=2,  # type: ignore[call-arg]
        _retry_delay=5,  # type: ignore[call-arg]
    )

    files.directory(
        name="Create MPP cmake build directory",
        path=build_path,
        _if=clone.did_succeed,
    )

    configure = server.shell(
        name="Configure MPP with cmake",
        commands=[
            f"cd {build_path} && cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON -DBUILD_TEST=OFF .."
        ],
        _if=clone.did_succeed,
    )

    build = server.shell(
        name="Build MPP libraries",
        commands=[f"cd {build_path} && make -j{parallel_jobs}"],
        _if=configure.did_succeed,
    )

    server.shell(
        name="Install MPP libraries",
        commands=[f"cd {build_path} && make install", "ldconfig"],
        _if=build.did_succeed,
    )


if __name__ == "__main__":
    rebuild = bool(host.data.get("rebuild", False))
    install_mpp(rebuild=rebuild, _sudo=True)
