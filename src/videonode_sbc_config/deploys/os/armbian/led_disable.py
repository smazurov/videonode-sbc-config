"""
Disable SBC LEDs using pyinfra.

This script uses Armbian-specific LED management scripts if available.

Usage:
    pyinfra @local deploys/os/armbian/led_disable.py
"""

from io import StringIO

from pyinfra.api.deploy import deploy
from pyinfra.context import host
from pyinfra.facts.files import File
from pyinfra.operations import files, server, systemd

SBC_LEDS = [
    {"name": "blue_led", "path": "/sys/class/leds/blue_led"},
    {"name": "green_led", "path": "/sys/class/leds/green_led"},
]
LED_CONFIG_FILE = "/etc/armbian-leds.conf"
LED_RESTORE_SCRIPT = "/usr/lib/armbian/armbian-led-state-restore.sh"


def _generate_led_config() -> str:
    """Generate LED configuration content."""
    config = "# SBC LED configuration - disabled by pyinfra\n"
    for led in SBC_LEDS:
        config += f"""
[{led["path"]}]
trigger=none

"""
    return config


def _generate_systemd_service() -> str:
    """Generate systemd service content for LED restore."""
    return f"""[Unit]
Description=Restore SBC LED state
After=local-fs.target
ConditionPathExists={LED_CONFIG_FILE}

[Service]
Type=oneshot
RemainAfterExit=true
ExecStart={LED_RESTORE_SCRIPT} {LED_CONFIG_FILE}
TimeoutSec=10

[Install]
WantedBy=sysinit.target
"""


@deploy("Disable SBC LEDs")
def disable_leds() -> None:
    """Disable SBC LEDs and configure persistence."""
    armbian_exists = host.get_fact(File, path=LED_RESTORE_SCRIPT)

    if armbian_exists:
        server.shell(
            name="Create LED state backup",
            commands=f"{LED_RESTORE_SCRIPT} {LED_CONFIG_FILE}.backup",
        )

    files.put(
        name="Create LED disable configuration",
        src=StringIO(_generate_led_config()),
        dest=LED_CONFIG_FILE,
        mode="0644",
        create_remote_dir=True,
    )

    led_commands = []
    for led in SBC_LEDS:
        led_commands.extend(
            [
                f"echo 'default-on' > {led['path']}/trigger 2>/dev/null || true",
                "sleep 0.1",
                f"echo 'none' > {led['path']}/trigger 2>/dev/null || true",
                f"echo '0' > {led['path']}/brightness 2>/dev/null || true",
            ]
        )

    server.shell(
        name="Apply LED configuration",
        commands=led_commands,
    )

    files.put(
        name="Create LED restore systemd service",
        src=StringIO(_generate_systemd_service()),
        dest="/etc/systemd/system/sbc-led-restore.service",
        mode="0644",
    )

    systemd.daemon_reload(
        name="Reload systemd daemon",
    )

    systemd.service(
        name="Enable SBC LED restore service",
        service="sbc-led-restore",
        enabled=True,
    )


if __name__ == "__main__":
    disable_leds(_sudo=True)
