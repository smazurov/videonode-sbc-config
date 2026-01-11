import subprocess
from importlib.resources import files

import click

from videonode_sbc_config.platform import detect_platform


@click.group()
def main():
    """SBC configuration for videonode streaming."""
    pass


@main.command()
@click.option("--board", default=None, help="Override detected board identifier")
def setup(board: str | None):
    """Run full hardware setup for detected platform."""
    platform = detect_platform()
    effective_board = board or platform.board
    click.echo(f"Detected platform: {platform}")
    if board:
        click.echo(f"Board override: {board}")

    if not platform.is_rockchip:
        raise click.ClickException(
            f"Unsupported SBC family: {platform.sbc_family.name}. "
            "Only Rockchip is currently supported."
        )
    if not platform.is_armbian:
        raise click.ClickException(
            f"Unsupported OS: {platform.os_type.name}. "
            "Only Armbian is currently supported."
        )

    deploys = files("videonode_sbc_config.deploys")
    scripts = [
        "hardware/rockchip/stack.py",
        "hardware/rockchip/permissions.py",
        "os/armbian/kernel_overlays.py",
        "generic/cockpit.py",
    ]
    for script in scripts:
        path = deploys.joinpath(script)
        click.echo(f"Running {script}...")
        cmd = ["pyinfra", "@local", str(path)]
        if script == "os/armbian/kernel_overlays.py":
            cmd.extend(["--data", f"board={effective_board}"])
        subprocess.run(cmd, check=True)
    click.echo("Setup complete. Reboot required for kernel overlays.")


@main.command()
@click.option("--token", required=True, help="Grafana Cloud API token")
@click.option("--username", required=True, help="Grafana Cloud username/user ID")
@click.option("--url", required=True, help="Grafana Cloud Prometheus push URL")
def alloy(token, username, url):
    """Setup Grafana Alloy metrics collection."""
    deploys = files("videonode_sbc_config.deploys")
    path = deploys.joinpath("generic/alloy.py")
    subprocess.run(
        [
            "pyinfra",
            "@local",
            str(path),
            "--data",
            f"grafana_cloud_token={token}",
            "--data",
            f"grafana_cloud_username={username}",
            "--data",
            f"grafana_cloud_url={url}",
        ],
        check=True,
    )


@main.command()
@click.option(
    "--verbose", "-v", is_flag=True, help="Show remediation hints for failures"
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def status(verbose: bool, as_json: bool):
    """Show SBC configuration status."""
    import json as json_module

    from videonode_sbc_config.deploys.verify import CheckStatus, run_all_checks
    from videonode_sbc_config.ui import render_dashboard

    platform = detect_platform()
    results = run_all_checks(platform)

    if as_json:
        data = {
            "platform": {
                "sbc_family": platform.sbc_family.name,
                "sbc_model": platform.sbc_model.name,
                "os_type": platform.os_type.name,
                "os_version": platform.os_version,
                "kernel_version": platform.kernel_version,
                "board": platform.board,
            },
            "checks": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "remediation": c.remediation,
                }
                for c in results
            ],
        }
        click.echo(json_module.dumps(data, indent=2))
    else:
        render_dashboard(platform, results, verbose=verbose)

    failed = sum(1 for r in results if r.status == CheckStatus.FAIL)
    raise SystemExit(failed)


if __name__ == "__main__":
    main()
