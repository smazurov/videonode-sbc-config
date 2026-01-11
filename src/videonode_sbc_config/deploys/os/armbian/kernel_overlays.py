"""
Manage kernel overlays for Armbian systems.

This module uses armbian-add-overlay to apply device tree overlays.
The overlay content is defined in hardware/<soc>/overlays.py.

Usage:
    pyinfra @local deploys/os/armbian/kernel_overlays.py
"""

from io import StringIO
from typing import TYPE_CHECKING

from pyinfra.context import host
from pyinfra.facts.files import File
from pyinfra.operations import files, server

if TYPE_CHECKING:
    pass

from videonode_sbc_config.deploys.hardware.rockchip.overlays import (
    OVERLAYS,
    get_overlays_for_board,
)

ARMBIAN_ADD_OVERLAY = "/usr/sbin/armbian-add-overlay"
ARMBIAN_ENV_TXT = "/boot/armbianEnv.txt"


def apply_overlay(name: str, content: str) -> None:
    """Apply a device tree overlay using armbian-add-overlay."""
    dts_path = f"/tmp/{name}.dts"

    files.put(
        name=f"Create {name} overlay",
        src=StringIO(content),
        dest=dts_path,
        mode="644",
    )

    server.shell(
        name=f"Apply {name} overlay with armbian-add-overlay",
        commands=[f"armbian-add-overlay {dts_path}"],
        _sudo=True,
    )

    # Add overlay to armbianEnv.txt for boot loading
    server.shell(
        name=f"Enable {name} overlay at boot",
        commands=[
            f"grep -q '^user_overlays=' {ARMBIAN_ENV_TXT} && sed -i '/^user_overlays=/s/$/ {name}/' {ARMBIAN_ENV_TXT} || echo 'user_overlays={name}' >> {ARMBIAN_ENV_TXT}",
            f"sed -i 's/user_overlays=\\s*/user_overlays=/' {ARMBIAN_ENV_TXT}",
        ],
        _sudo=True,
    )

    files.file(
        name=f"Clean up {name} overlay source",
        path=dts_path,
        present=False,
    )


# Check if armbian-add-overlay exists
has_armbian_overlay = host.get_fact(File, ARMBIAN_ADD_OVERLAY)

if not has_armbian_overlay:
    print(
        f"ERROR: {ARMBIAN_ADD_OVERLAY} not found. This tool comes with Armbian by default."
    )
    print("If missing, you may need to reinstall Armbian or check your installation.")
    exit(1)

# Get board from pyinfra data (passed via --data board=xxx)
board: str = host.data.get("board") or ""
overlays_to_apply = get_overlays_for_board(board)

print(f"Board: {board or '(unknown)'}")
print(f"Applying overlays: {', '.join(overlays_to_apply)}")

for overlay_name in overlays_to_apply:
    if overlay_name in OVERLAYS:
        apply_overlay(overlay_name, OVERLAYS[overlay_name])

print("Reboot required for overlay changes to take effect")
