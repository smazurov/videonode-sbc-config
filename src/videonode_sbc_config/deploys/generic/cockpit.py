"""
Deploy Cockpit web console with cockpit-navigator file manager.

Usage:
    pyinfra inventory.py deploys/generic/cockpit.py
"""

from typing import TYPE_CHECKING
from io import StringIO

from pyinfra import logger
from pyinfra.context import host
from pyinfra.operations import apt, server, files
from pyinfra.facts.server import Home
from pyinfra.facts.deb import DebPackage

if TYPE_CHECKING:
    pass

# Get home directory from remote host
USER_HOME = host.get_fact(Home)

# Cockpit configuration
COCKPIT_PORT = 9890

# Install Cockpit and related packages (excluding VM stuff)
apt.packages(
    name="Install Cockpit packages",
    packages=[
        "cockpit",
        "cockpit-ws",
        "cockpit-system",
        "cockpit-storaged",
        "cockpit-networkmanager",  # For viewing network info
    ],
    update=True,
    _sudo=True,
)

# Create systemd override directory for cockpit socket
files.directory(
    name="Create cockpit socket override directory",
    path="/etc/systemd/system/cockpit.socket.d",
    _sudo=True,
)

# Configure cockpit to use port 9890
cockpit_socket_override = f"""[Socket]
ListenStream=
ListenStream={COCKPIT_PORT}
"""

files.put(
    name="Configure cockpit socket port",
    dest="/etc/systemd/system/cockpit.socket.d/override.conf",
    src=StringIO(cockpit_socket_override),
    mode="644",
    _sudo=True,
)

# Check if cockpit-navigator is already installed
navigator_installed = host.get_fact(DebPackage, "cockpit-navigator")

if not navigator_installed:
    # Download cockpit-navigator deb package
    files.download(
        name="Download cockpit-navigator deb package",
        src="https://github.com/45Drives/cockpit-navigator/releases/download/v0.5.10/cockpit-navigator_0.5.10-1focal_all.deb",
        dest="/tmp/cockpit-navigator.deb",
    )

    # Install cockpit-navigator from deb package
    server.shell(
        name="Install cockpit-navigator",
        commands=["dpkg -i /tmp/cockpit-navigator.deb || apt-get install -f -y"],
        _sudo=True,
    )

    # Clean up downloaded deb package
    files.file(
        name="Remove cockpit-navigator deb package",
        path="/tmp/cockpit-navigator.deb",
        present=False,
    )
else:
    logger.info("cockpit-navigator already installed, skipping download")

# Reload systemd daemon to pick up socket configuration changes
server.shell(
    name="Reload systemd daemon",
    commands=["systemctl daemon-reload"],
    _sudo=True,
)

# Enable and restart cockpit socket to pick up port change
server.shell(
    name="Enable and restart cockpit socket",
    commands=[
        "systemctl enable cockpit.socket",
        "systemctl restart cockpit.socket",
    ],
    _sudo=True,
)

logger.info(
    f"Cockpit web console will be available at https://<host-ip>:{COCKPIT_PORT}"
)
