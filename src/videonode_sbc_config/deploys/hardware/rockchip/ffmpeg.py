"""
Install FFmpeg with Rockchip hardware acceleration using pyinfra.

Usage:
    pyinfra @local deploys/hardware/rockchip/ffmpeg.py
    pyinfra @local deploys/hardware/rockchip/ffmpeg.py --data rebuild=true
"""

from typing import TYPE_CHECKING

from pyinfra.context import host
from pyinfra.operations import apt, server, files
from pyinfra.facts.files import File
from pyinfra.facts.server import Home

if TYPE_CHECKING:
    pass

from videonode_sbc_config.deploys.utils import get_build_dependencies, get_parallel_jobs

# Get home directory from remote host
USER_HOME = host.get_fact(Home)

# Build paths as constants
BUILD_BASE = f"{USER_HOME}/dev"
BUILD_DIR = f"{BUILD_BASE}/ffmpeg"
PARALLEL_JOBS = get_parallel_jobs()

# Check for rebuild flag from command line
REBUILD = host.data.get("rebuild", False)

# Check if FFmpeg already installed
ffmpeg_installed = host.get_fact(File, "/usr/bin/ffmpeg")


if REBUILD or not ffmpeg_installed:
    # Remove existing FFmpeg directory to ensure clean state for rebuild
    if REBUILD:
        files.directory(
            name="Remove existing FFmpeg directory for rebuild",
            path=BUILD_DIR,
            present=False,
        )
    # Install build dependencies using pyinfra apt operations
    apt.packages(
        name="Install FFmpeg build dependencies",
        packages=get_build_dependencies("base", "ffmpeg"),
        update=True,
        _sudo=True,
        _ignore_errors=False,
    )

    # Ensure build directory exists
    files.directory(
        name="Create FFmpeg build directory",
        path=BUILD_BASE,
    )

    # Clone FFmpeg repository using shell command to avoid pyinfra git.repo issues
    server.shell(
        name="Clone FFmpeg Rockchip repository",
        commands=[
            f"[ -d {BUILD_DIR} ] || git clone -b 7.1 https://github.com/nyanmisaka/ffmpeg-rockchip.git {BUILD_DIR}"
        ],
    )

    # Configure FFmpeg
    server.shell(
        name="Configure FFmpeg with Rockchip support",
        commands=[
            f"cd {BUILD_DIR} && ./configure --prefix=/usr --enable-gpl --enable-version3 --enable-libdrm --enable-rkmpp --enable-rkrga --enable-libopus --enable-libfreetype --enable-libharfbuzz --enable-libfontconfig --enable-libsrt"
        ],
        _ignore_errors=False,
    )

    # Build FFmpeg
    server.shell(
        name="Build FFmpeg",
        commands=[f"cd {BUILD_DIR} && make -j{PARALLEL_JOBS}"],
        _ignore_errors=False,
    )

    # Install FFmpeg (needs sudo for system install)
    server.shell(
        name="Install FFmpeg",
        commands=[f"cd {BUILD_DIR} && make install", "ldconfig"],
        _sudo=True,
        _ignore_errors=False,
    )
