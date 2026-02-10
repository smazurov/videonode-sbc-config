"""
Install FFmpeg with Rockchip hardware acceleration using pyinfra.

Usage:
    pyinfra @local deploys/hardware/rockchip/ffmpeg.py
    pyinfra @local deploys/hardware/rockchip/ffmpeg.py --data rebuild=true
"""

from pyinfra.api.deploy import deploy
from pyinfra.context import host
from pyinfra.facts.server import Home
from pyinfra.operations import apt, files, server

from videonode_sbc_config.deploys.utils import get_build_dependencies, get_parallel_jobs

FFMPEG_VERSION = "7.1"
FFMPEG_REPO = "https://github.com/nyanmisaka/ffmpeg-rockchip.git"


@deploy("Install FFmpeg")
def install_ffmpeg(rebuild: bool = False) -> None:
    """Install FFmpeg with Rockchip hardware acceleration."""
    user_home = host.get_fact(Home)
    build_base = f"{user_home}/dev"
    build_dir = f"{build_base}/ffmpeg"
    parallel_jobs = get_parallel_jobs()

    deps = apt.packages(
        name="Install FFmpeg build dependencies",
        packages=get_build_dependencies("base", "ffmpeg"),
        update=True,
    )

    files.directory(
        name="Create FFmpeg build directory",
        path=build_base,
        _if=deps.did_succeed,
    )

    files.directory(
        name="Remove existing FFmpeg directory if present",
        path=build_dir,
        present=False,
        _if=deps.did_succeed,
    )

    clone = server.shell(
        name="Clone FFmpeg Rockchip repository",
        commands=[
            f"git clone --depth 1 --branch {FFMPEG_VERSION} {FFMPEG_REPO} {build_dir}"
        ],
        _if=deps.did_succeed,
        _retries=2,  # type: ignore[call-arg]
        _retry_delay=5,  # type: ignore[call-arg]
    )

    configure = server.shell(
        name="Configure FFmpeg with Rockchip support",
        commands=[
            f"cd {build_dir} && ./configure --prefix=/usr --enable-gpl --enable-version3 --enable-libdrm --enable-rkmpp --enable-rkrga --enable-libopus --enable-libfreetype --enable-libharfbuzz --enable-libfontconfig --enable-libsrt"
        ],
        _if=clone.did_succeed,
    )

    build = server.shell(
        name="Build FFmpeg",
        commands=[f"cd {build_dir} && make -j{parallel_jobs}"],
        _if=configure.did_succeed,
    )

    server.shell(
        name="Install FFmpeg",
        commands=[f"cd {build_dir} && make install", "ldconfig"],
        _if=build.did_succeed,
    )


if __name__ == "__main__":
    rebuild = bool(host.data.get("rebuild", False))
    install_ffmpeg(rebuild=rebuild, _sudo=True)
