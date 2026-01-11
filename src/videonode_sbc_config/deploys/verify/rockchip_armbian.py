"""Verification checks for Rockchip SBCs on Armbian."""

from videonode_sbc_config.deploys.hardware.rockchip.overlays import OVERLAYS
from videonode_sbc_config.platform import Platform

from .runner import run_check
from .types import CheckResult, CheckStatus


def get_checks(platform: Platform) -> list[CheckResult]:
    """Return verification checks for Rockchip + Armbian."""
    if not platform.is_rockchip:
        return [CheckResult("Platform", CheckStatus.SKIP, "Not Rockchip")]
    if not platform.is_armbian:
        return [CheckResult("Platform", CheckStatus.SKIP, "Not Armbian")]

    results: list[CheckResult] = []

    # Boot device
    results.append(
        run_check(
            "Boot device",
            "lsblk -no PKNAME $(findmnt -n -o SOURCE /)",
            lambda x: x == "mmcblk0",
            pass_msg="eMMC",
            fail_msg="Not eMMC ({result})",
        )
    )

    # eMMC device
    results.append(
        run_check(
            "eMMC device",
            "test -b /dev/mmcblk0 && lsblk -dn -o SIZE /dev/mmcblk0 || echo 'missing'",
            lambda x: x != "missing",
            pass_msg="{result}",
            fail_msg="Not found",
        )
    )

    # Partition expansion
    results.append(
        run_check(
            "Partition expansion",
            """
            root_part=$(findmnt -n -o SOURCE /)
            df_output=$(df -B1 $root_part | tail -1)
            fs_size=$(echo $df_output | awk '{print $2}')
            part_size=$(lsblk -b -n -o SIZE $root_part)
            if [ "$part_size" -gt 0 ] && [ "$fs_size" -gt 0 ]; then
                percent=$((fs_size * 100 / part_size))
                echo "$percent"
            else
                echo "0"
            fi
            """,
            lambda x: int(x) >= 95 if x.isdigit() else False,
            fail_msg="Not using full partition",
        )
    )

    # Root filesystem usage
    results.append(
        run_check(
            "Root filesystem usage",
            "df / | tail -1 | awk '{print $5}'",
            lambda x: int(x.strip("%")) < 90 if x.strip("%").isdigit() else False,
            pass_msg="{result}",
            fail_msg="{result} (too high)",
        )
    )

    # Blue LED
    results.append(
        run_check(
            "Blue LED",
            "cat /sys/class/leds/blue_led/trigger 2>/dev/null | grep -o '\\[.*\\]' | tr -d '[]' || echo 'error'",
            lambda x: x == "none",
            pass_msg="Disabled",
            fail_msg="LED is on",
        )
    )

    # Green LED
    results.append(
        run_check(
            "Green LED",
            "cat /sys/class/leds/green_led/trigger 2>/dev/null | grep -o '\\[.*\\]' | tr -d '[]' || echo 'error'",
            lambda x: x == "none",
            pass_msg="Disabled",
            fail_msg="LED is on",
        )
    )

    # FFmpeg encoders
    results.append(
        run_check(
            "FFmpeg encoders",
            "ffmpeg -encoders 2>/dev/null | grep -c rkmpp || echo '0'",
            lambda x: int(x) >= 2 if x.isdigit() else False,
            pass_msg="{result}",
            fail_msg="{result}",
        )
    )

    # MPP device permissions
    results.append(
        run_check(
            "MPP permissions",
            "ls -l /dev/mpp_service 2>/dev/null | awk '{print $1}' || echo 'missing'",
            lambda x: x.startswith("crw-rw-rw-") if x != "missing" else False,
            pass_msg="666",
            fail_msg="Needs fix",
        )
    )

    # RGA device permissions
    results.append(
        run_check(
            "RGA permissions",
            "ls -l /dev/rga 2>/dev/null | awk '{print $1}' || echo 'missing'",
            lambda x: x.startswith("crw-rw-rw-") if x != "missing" else False,
            pass_msg="666",
            fail_msg="Needs fix",
        )
    )

    # DMA heap permissions
    results.append(
        run_check(
            "DMA heap permissions",
            "ls -l /dev/dma_heap/system 2>/dev/null | awk '{print $1}' || echo 'missing'",
            lambda x: x.startswith("crw-rw-rw-") if x != "missing" else False,
            pass_msg="666",
            fail_msg="Needs fix",
        )
    )

    # Kernel overlays (dynamic from OVERLAYS list)
    for overlay in OVERLAYS:
        results.append(
            run_check(
                f"Overlay: {overlay.name}",
                f"ls /boot/overlay-user/{overlay.id}.dtbo 2>/dev/null && echo 'Installed' || echo 'Not installed'",
            )
        )

    # Cockpit web UI
    results.append(
        run_check(
            "Cockpit",
            "systemctl is-active cockpit.socket 2>/dev/null || echo 'inactive'",
            lambda x: x == "active",
            pass_msg="Running",
            fail_msg="Not installed",
        )
    )

    return results
