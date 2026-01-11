"""
Setup LED permissions for SBC LED control via sysfs.
Allows non-root users in the video group to control LEDs.

Usage:
    pyinfra @local deploys/generic/led_permissions.py
"""

from io import StringIO
from typing import TYPE_CHECKING

from pyinfra.operations import files, server

if TYPE_CHECKING:
    pass

# Create udev rules for LED access
files.put(
    name="Setup LED permissions",
    src=StringIO("""# LED sysfs permissions for videonode
# Allows users in the video group to control LEDs
SUBSYSTEM=="leds", ACTION=="add", RUN+="/bin/chgrp -R video /sys%p", RUN+="/bin/chmod -R g=u /sys%p"
SUBSYSTEM=="leds", ACTION=="change", RUN+="/bin/chgrp -R video /sys%p", RUN+="/bin/chmod -R g=u /sys%p"
"""),
    dest="/etc/udev/rules.d/99-led-permissions.rules",
    mode="644",
    _sudo=True,
    _ignore_errors=False,
)

# Reload udev rules
server.shell(
    name="Reload udev rules",
    commands=[
        "udevadm control --reload-rules",
        "udevadm trigger --subsystem-match=leds",
    ],
    _sudo=True,
    _ignore_errors=False,
)
