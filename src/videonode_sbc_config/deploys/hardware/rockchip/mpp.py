"""
Install Rockchip MPP (Media Process Platform) using pyinfra.

Usage:
    pyinfra @local deploys/hardware/rockchip/mpp.py
    pyinfra @local deploys/hardware/rockchip/mpp.py --data rebuild=true
"""

from typing import TYPE_CHECKING

from pyinfra.context import host
from pyinfra.operations import apt, files, server
from pyinfra.facts.files import File
from pyinfra.facts.server import Home

if TYPE_CHECKING:
    pass

from videonode_sbc_config.deploys.utils import get_build_dependencies, get_parallel_jobs

# Get home directory from remote host
USER_HOME = host.get_fact(Home)

# Build paths as constants
BUILD_BASE = f"{USER_HOME}/dev"
BUILD_DIR = f"{BUILD_BASE}/rkmpp"
BUILD_PATH = f"{BUILD_DIR}/build"
PARALLEL_JOBS = get_parallel_jobs()

# Check for rebuild flag from command line
REBUILD = host.data.get("rebuild", False)

# Check if MPP is already installed by looking for mpp_info_test binary
mpp_installed = host.get_fact(File, "/usr/local/bin/mpp_info_test")

if REBUILD or not mpp_installed:
    # Install build dependencies (needs sudo for apt)
    apt.packages(
        name="Install MPP build dependencies",
        packages=get_build_dependencies("base", "mpp"),
        update=True,
        _sudo=True,
        _ignore_errors=False,
    )

    # Ensure build directory exists
    files.directory(
        name="Create MPP build directory",
        path=BUILD_BASE,
    )

    # Remove existing MPP directory to ensure clean state
    files.directory(
        name="Remove existing MPP directory if present",
        path=BUILD_DIR,
        present=False,
    )

    # Shallow clone MPP repository at specific tag (HermanChen fork with fixes)
    server.shell(
        name="Clone Rockchip MPP repository",
        commands=[
            f"git clone --depth 1 --branch 1.0.10 https://github.com/HermanChen/mpp.git {BUILD_DIR}"
        ],
        _ignore_errors=False,
    )

    # Create build directory
    files.directory(
        name="Create MPP cmake build directory",
        path=BUILD_PATH,
    )

    # Configure MPP with cmake
    server.shell(
        name="Configure MPP with cmake",
        commands=[
            f"cd {BUILD_PATH} && cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON -DBUILD_TEST=OFF .."
        ],
        _ignore_errors=False,
    )

    # Build MPP
    server.shell(
        name="Build MPP libraries",
        commands=[f"cd {BUILD_PATH} && make -j{PARALLEL_JOBS}"],
        _ignore_errors=False,
    )

    # Install MPP (needs sudo for system install)
    server.shell(
        name="Install MPP libraries",
        commands=[f"cd {BUILD_PATH} && make install", "ldconfig"],
        _sudo=True,
        _ignore_errors=False,
    )
