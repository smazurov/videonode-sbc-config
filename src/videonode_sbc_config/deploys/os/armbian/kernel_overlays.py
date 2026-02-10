"""
Manage kernel overlays for Armbian systems.

This module uses armbian-add-overlay to apply device tree overlays.
The overlay content is defined in hardware/<soc>/overlays.py.

Usage:
    pyinfra @local deploys/os/armbian/kernel_overlays.py --data overlay_id=usb-host-mode
"""

from io import StringIO

from pyinfra import logger
from pyinfra.api.deploy import deploy
from pyinfra.context import host
from pyinfra.facts.files import File
from pyinfra.operations import files, server

from videonode_sbc_config.deploys.hardware.rockchip.overlays import get_overlay

ARMBIAN_ADD_OVERLAY = "/usr/sbin/armbian-add-overlay"
ARMBIAN_ENV_TXT = "/boot/armbianEnv.txt"


@deploy("Apply kernel overlay")
def apply_overlay(overlay_id: str, dts_content: str) -> None:
    """Apply a device tree overlay using armbian-add-overlay."""
    dts_path = f"/tmp/{overlay_id}.dts"

    put_dts = files.put(
        name=f"Create {overlay_id} overlay",
        src=StringIO(dts_content),
        dest=dts_path,
        mode="644",
    )

    apply_cmd = server.shell(
        name=f"Apply {overlay_id} overlay with armbian-add-overlay",
        commands=[f"armbian-add-overlay {dts_path}"],
        _if=put_dts.did_succeed,
    )

    server.shell(
        name=f"Enable {overlay_id} overlay at boot",
        commands=[
            f"grep -q '^user_overlays=' {ARMBIAN_ENV_TXT} && sed -i '/^user_overlays=/s/$/ {overlay_id}/' {ARMBIAN_ENV_TXT} || echo 'user_overlays={overlay_id}' >> {ARMBIAN_ENV_TXT}",
            f"sed -i 's/user_overlays=\\s*/user_overlays=/' {ARMBIAN_ENV_TXT}",
        ],
        _if=apply_cmd.did_succeed,
    )

    files.file(
        name=f"Clean up {overlay_id} overlay source",
        path=dts_path,
        present=False,
    )


if __name__ == "__main__":
    has_armbian_overlay = host.get_fact(File, ARMBIAN_ADD_OVERLAY)

    if not has_armbian_overlay:
        logger.error(
            f"{ARMBIAN_ADD_OVERLAY} not found. This tool comes with Armbian by default."
        )
        exit(1)

    overlay_id: str = host.data.get("overlay_id") or ""

    if not overlay_id:
        logger.error("No overlay_id specified. Use --data overlay_id=<id>")
        exit(1)

    overlay = get_overlay(overlay_id)
    if not overlay:
        logger.error(f"Unknown overlay: {overlay_id}")
        exit(1)

    logger.info(f"Installing overlay: {overlay.name}")
    apply_overlay(overlay_id=overlay.id, dts_content=overlay.dts, _sudo=True)
    logger.info("Reboot required for overlay changes to take effect")
