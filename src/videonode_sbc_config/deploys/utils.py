"""
Shared utilities for pyinfra SBC deployments.
"""

import os

from pyinfra.api.host import Host
from pyinfra.api.state import State
from pyinfra.operations import files


def get_parallel_jobs() -> int:
    """Get number of parallel build jobs based on CPU count."""
    return os.cpu_count() or 4


def ensure_build_dir(state: State, host: Host, path: str) -> None:
    """Create and ensure build directory exists."""
    files.directory(
        name=f"Ensure build directory {path} exists",
        path=path,
        _sudo=True,
    )


def get_build_dir(base: str = "/root/dev", project: str = "") -> str:
    """Get standardized build directory path."""
    if project:
        return f"{base}/{project}"
    return base


# Common build dependencies for different projects
BUILD_DEPS = {
    "base": [
        "build-essential",
        "git",
        "pkg-config",
        "cmake",
        "wget",
        "curl",
        "v4l-utils",
    ],
    "ffmpeg": [
        "yasm",
        "nasm",
        "libdrm-dev",
        "libasound2-dev",
        "libopus-dev",
        "libfreetype6-dev",
        "libharfbuzz-dev",
        "libfontconfig1-dev",
        "libsrt-openssl-dev",
        "libssl-dev",
    ],
    "mpp": [
        "libdrm-dev",
    ],
    "rga": [
        "libdrm-dev",
        "meson",
        "ninja-build",
    ],
}


def get_build_dependencies(*categories: str) -> list[str]:
    """Get combined list of build dependencies for given categories."""
    deps = set()
    for category in categories:
        if category in BUILD_DEPS:
            deps.update(BUILD_DEPS[category])
    return sorted(list(deps))
