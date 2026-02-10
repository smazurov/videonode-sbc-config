"""
Deploy Cockpit web console with cockpit-navigator file manager.

Usage:
    pyinfra @local deploys/generic/cockpit.py
"""

from io import StringIO

from pyinfra import logger
from pyinfra.api.deploy import deploy
from pyinfra.facts.deb import DebPackage
from pyinfra.operations import apt, files, server

COCKPIT_PORT = 9890
NAVIGATOR_URL = "https://github.com/45Drives/cockpit-navigator/releases/download/v0.5.10/cockpit-navigator_0.5.10-1focal_all.deb"


@deploy("Setup Cockpit")
def install_cockpit() -> None:
    """Install Cockpit web console with file manager."""
    apt_install = apt.packages(
        name="Install Cockpit packages",
        packages=[
            "cockpit",
            "cockpit-ws",
            "cockpit-system",
            "cockpit-storaged",
            "cockpit-networkmanager",
        ],
        update=True,
    )

    files.directory(
        name="Create cockpit socket override directory",
        path="/etc/systemd/system/cockpit.socket.d",
        _if=apt_install.did_succeed,
    )

    socket_override = f"""[Socket]
ListenStream=
ListenStream={COCKPIT_PORT}
"""

    socket_put = files.put(
        name="Configure cockpit socket port",
        dest="/etc/systemd/system/cockpit.socket.d/override.conf",
        src=StringIO(socket_override),
        mode="644",
        _if=apt_install.did_succeed,
    )

    # Check if navigator already installed and download if needed
    from pyinfra.context import host

    navigator_installed = host.get_fact(DebPackage, "cockpit-navigator")

    download = files.download(
        name="Download cockpit-navigator deb package",
        src=NAVIGATOR_URL,
        dest="/tmp/cockpit-navigator.deb",
        _if=lambda: not navigator_installed,
    )

    server.shell(
        name="Install cockpit-navigator",
        commands=["dpkg -i /tmp/cockpit-navigator.deb || apt-get install -f -y"],
        _if=download.did_change,
    )

    files.file(
        name="Remove cockpit-navigator deb package",
        path="/tmp/cockpit-navigator.deb",
        present=False,
        _if=download.did_change,
    )

    server.shell(
        name="Reload systemd daemon",
        commands=["systemctl daemon-reload"],
        _if=socket_put.did_change,
    )

    server.shell(
        name="Enable and restart cockpit socket",
        commands=[
            "systemctl enable cockpit.socket",
            "systemctl restart cockpit.socket",
        ],
        _if=apt_install.did_succeed,
    )

    logger.info(f"Cockpit web console available at https://<host-ip>:{COCKPIT_PORT}")


if __name__ == "__main__":
    install_cockpit(_sudo=True)
