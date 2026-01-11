"""Verification checks for Rockchip SBCs on Armbian."""

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
            remediation="videonode-sbc-config setup",
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
            remediation="videonode-sbc-config setup",
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
            remediation="videonode-sbc-config setup",
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
            remediation="videonode-sbc-config setup",
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
            remediation="videonode-sbc-config setup",
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
            remediation="videonode-sbc-config setup",
        )
    )

    # USB host overlay
    results.append(
        run_check(
            "USB host overlay",
            "ls /boot/overlay-user/usb-host-mode.dtbo 2>/dev/null && echo 'installed' || echo 'missing'",
            lambda x: "installed" in x,
            pass_msg="Installed",
            fail_msg="Not installed",
            remediation="videonode-sbc-config setup",
        )
    )

    # HDMI RX disable overlay
    results.append(
        run_check(
            "HDMI RX overlay",
            "ls /boot/overlay-user/disable-hdmirx.dtbo 2>/dev/null && echo 'installed' || echo 'missing'",
            lambda x: "installed" in x,
            pass_msg="Installed",
            fail_msg="Not installed",
            remediation="videonode-sbc-config setup",
        )
    )

    # Overlays in boot config
    results.append(
        run_check(
            "Boot config overlays",
            "grep '^user_overlays=' /boot/armbianEnv.txt 2>/dev/null || echo 'none'",
            lambda x: "usb-host-mode" in x and "disable-hdmirx" in x
            if x != "none"
            else False,
            pass_msg="Configured",
            fail_msg="Missing in armbianEnv.txt",
            remediation="videonode-sbc-config setup",
        )
    )

    return results
