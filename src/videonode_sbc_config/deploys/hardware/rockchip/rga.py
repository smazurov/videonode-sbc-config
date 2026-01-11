"""
Install Rockchip RGA (2D Graphics Acceleration) using pyinfra.

Usage:
    pyinfra @local deploys/hardware/rockchip/rga.py
    pyinfra @local deploys/hardware/rockchip/rga.py --data rebuild=true
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
BUILD_DIR = f"{BUILD_BASE}/rkrga"
BUILD_PATH = f"{BUILD_DIR}/build"
PARALLEL_JOBS = get_parallel_jobs()

# Check for rebuild flag from command line
REBUILD = host.data.get("rebuild", False)

# Check if RGA is already installed by looking for librga.so
rga_installed = host.get_fact(File, "/usr/local/lib/librga.so")

if REBUILD or not rga_installed:
    # Install build dependencies (needs sudo for apt)
    apt.packages(
        name="Install RGA build dependencies",
        packages=get_build_dependencies("base", "rga"),
        update=True,
        _sudo=True,
        _ignore_errors=False,
    )

    # Ensure build directory exists
    files.directory(
        name="Create RGA build directory",
        path=BUILD_BASE,
    )

    # Remove existing RGA directory to ensure clean state
    files.directory(
        name="Remove existing RGA directory if present",
        path=BUILD_DIR,
        present=False,
    )

    # Clone RGA repository with depth=1 and specific branch
    server.shell(
        name="Shallow Clone Rockchip RGA repository",
        commands=[
            f"git clone --depth=1 --branch jellyfin-rga https://github.com/nyanmisaka/rk-mirrors.git {BUILD_DIR}"
        ],
    )

    # Configure RGA with meson (creates build directory inside rkrga)
    server.shell(
        name="Configure RGA with meson",
        commands=[
            f"cd {BUILD_DIR} && meson setup build --prefix=/usr --libdir=lib --buildtype=release --default-library=shared -Dcpp_args=-fpermissive -Dlibdrm=false -Dlibrga_demo=false"
        ],
        _ignore_errors=False,
    )

    # Build and install RGA
    server.shell(
        name="Build and install RGA libraries",
        commands=[
            f"cd {BUILD_PATH} && ninja",
            f"cd {BUILD_PATH} && ninja install",
            "ldconfig",
        ],
        _sudo=True,
        _ignore_errors=False,
    )
