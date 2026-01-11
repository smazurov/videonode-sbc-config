import json as json_module
import sys

import click

from videonode_sbc_config.platform import detect_platform


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """SBC configuration for videonode streaming."""
    if ctx.invoked_subcommand is None:
        from videonode_sbc_config.ui import run_interactive

        platform = detect_platform()
        run_interactive(platform)


@main.command()
@click.option(
    "--verbose", "-v", is_flag=True, help="Show remediation hints for failures"
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def status(verbose: bool, as_json: bool) -> None:
    """Show SBC configuration status (non-interactive)."""
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
    sys.exit(failed)


@main.command()
@click.option("--token", required=True, help="Grafana Cloud API token")
@click.option("--username", required=True, help="Grafana Cloud username/user ID")
@click.option("--url", required=True, help="Grafana Cloud Prometheus push URL")
def alloy(token: str, username: str, url: str) -> None:
    """Setup Grafana Alloy metrics collection."""
    import subprocess
    from importlib.resources import files

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


if __name__ == "__main__":
    main()
