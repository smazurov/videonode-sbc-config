"""
Disable SBC LEDs using pyinfra.

This script uses Armbian-specific LED management scripts if available.

Usage:
    pyinfra @local deploys/os/armbian/led_disable.py
"""

from io import StringIO
from typing import TYPE_CHECKING

from pyinfra.context import host
from pyinfra.operations import files, server, systemd
from pyinfra.facts.files import File

if TYPE_CHECKING:
    pass

# Configuration
SBC_LEDS = [
    {"name": "blue_led", "path": "/sys/class/leds/blue_led"},
    {"name": "green_led", "path": "/sys/class/leds/green_led"},
]
LED_CONFIG_FILE = "/etc/armbian-leds.conf"
LED_RESTORE_SCRIPT = "/usr/lib/armbian/armbian-led-state-restore.sh"


def generate_led_config() -> str:
    """Generate LED configuration content."""
    config = "# SBC LED configuration - disabled by pyinfra\n"
    for led in SBC_LEDS:
        config += f"""
[{led["path"]}]
trigger=none

"""
    return config


def generate_systemd_service() -> str:
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


def disable_leds() -> None:
    """Disable SBC LEDs."""
    # Check if Armbian LED management exists
    armbian_exists = host.get_fact(File, path=LED_RESTORE_SCRIPT)

    # Create LED state backup if Armbian scripts exist
    if armbian_exists:
        server.shell(
            name="Create LED state backup",
            commands=f"{LED_RESTORE_SCRIPT} {LED_CONFIG_FILE}.backup",
            _sudo=True,
        )

    # Create LED disable configuration
    files.put(
        name="Create LED disable configuration",
        src=StringIO(generate_led_config()),
        dest=LED_CONFIG_FILE,
        mode="0644",
        create_remote_dir=True,
        _sudo=True,
    )

    # Apply LED configuration immediately
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
        _sudo=True,
    )

    # Create LED restore systemd service
    files.put(
        name="Create LED restore systemd service",
        src=StringIO(generate_systemd_service()),
        dest="/etc/systemd/system/sbc-led-restore.service",
        mode="0644",
        _sudo=True,
    )

    # Reload systemd daemon
    systemd.daemon_reload(
        name="Reload systemd daemon",
        _sudo=True,
    )

    # Enable LED restore service
    systemd.service(
        name="Enable SBC LED restore service",
        service="sbc-led-restore",
        enabled=True,
        _sudo=True,
    )


# Main execution
disable_leds()
