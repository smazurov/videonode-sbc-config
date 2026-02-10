"""
Setup LED permissions for SBC LED control via sysfs.
Allows non-root users in the video group to control LEDs.

Usage:
    pyinfra @local deploys/generic/led_permissions.py
"""

from io import StringIO

from pyinfra.api.deploy import deploy
from pyinfra.operations import files, server

UDEV_RULES = """# LED sysfs permissions for videonode
# Allows users in the video group to control LEDs
SUBSYSTEM=="leds", ACTION=="add", RUN+="/bin/chgrp -R video /sys%p", RUN+="/bin/chmod -R g=u /sys%p"
SUBSYSTEM=="leds", ACTION=="change", RUN+="/bin/chgrp -R video /sys%p", RUN+="/bin/chmod -R g=u /sys%p"
"""


@deploy("Setup LED permissions")
def setup_led_permissions() -> None:
    """Configure udev rules for LED access by video group."""
    put_rules = files.put(
        name="Setup LED permissions",
        src=StringIO(UDEV_RULES),
        dest="/etc/udev/rules.d/99-led-permissions.rules",
        mode="644",
    )

    server.shell(
        name="Reload udev rules",
        commands=[
            "udevadm control --reload-rules",
            "udevadm trigger --subsystem-match=leds",
        ],
        _if=put_rules.did_change,
    )


if __name__ == "__main__":
    setup_led_permissions(_sudo=True)
