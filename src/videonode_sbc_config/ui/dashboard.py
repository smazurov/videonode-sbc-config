"""Rich dashboard rendering for status checks."""

import subprocess
import sys
from importlib.resources import files

import readchar
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from videonode_sbc_config.deploys.verify import CheckResult, CheckStatus, run_all_checks
from videonode_sbc_config.platform import Platform

from .components import InstallableComponent, get_components_for_platform

STATUS_ICONS = {
    CheckStatus.PASS: "[green]OK[/green]",
    CheckStatus.FAIL: "[red]FAIL[/red]",
    CheckStatus.INFO: "[dim]-[/dim]",
    CheckStatus.SKIP: "[dim]SKIP[/dim]",
}


def _compute_component_status(
    component: InstallableComponent, results: list[CheckResult]
) -> CheckStatus:
    check_map = {r.name: r for r in results}
    statuses = []
    for check_name in component.checks:
        if check_name in check_map:
            statuses.append(check_map[check_name].status)
    if not statuses:
        return CheckStatus.SKIP
    if any(s == CheckStatus.FAIL for s in statuses):
        return CheckStatus.FAIL
    if all(s == CheckStatus.PASS for s in statuses):
        return CheckStatus.PASS
    return CheckStatus.INFO


def _build_platform_panel(platform: Platform) -> Panel:
    platform_info = f"Board:   {platform.board or '(unknown)'}\n"
    platform_info += (
        f"SBC:     {platform.sbc_family.name}/{platform.sbc_model.name}\n"
        f"OS:      {platform.os_type.name}"
    )
    if platform.os_version:
        platform_info += f" {platform.os_version}"
    platform_info += f"\nKernel:  {platform.kernel_version}"
    return Panel(platform_info, title="Platform")


def _build_components_table(
    components: list[InstallableComponent], results: list[CheckResult]
) -> Panel:
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("#", style="cyan", width=3)
    table.add_column("Component", min_width=18)
    table.add_column("Status", justify="center", width=6)
    table.add_column("Description", min_width=20)

    for comp in components:
        status = _compute_component_status(comp, results)
        table.add_row(
            f"[{comp.key}]",
            comp.name,
            STATUS_ICONS[status],
            comp.help_text,
        )

    return Panel(table, title="Components")


def _build_system_info_table(
    results: list[CheckResult], components: list[InstallableComponent]
) -> Panel:
    component_check_names = set()
    for comp in components:
        component_check_names.update(comp.checks)

    table = Table(show_header=False, box=None)
    table.add_column("Check", style="cyan", min_width=20)
    table.add_column("Status", justify="center", width=6)
    table.add_column("Details", min_width=20)

    for check in results:
        if check.name not in component_check_names:
            table.add_row(check.name, STATUS_ICONS[check.status], check.message)

    return Panel(table, title="System Info")


def _build_footer(components: list[InstallableComponent]) -> Text:
    if not components:
        return Text("Unsupported platform. Press q to quit.", style="dim")
    max_key = max(int(c.key) for c in components)
    return Text(f"Press 1-{max_key} to install, q to quit", style="dim")


def _run_install(
    component: InstallableComponent, platform: Platform, console: Console
) -> None:
    console.clear()
    console.print(f"\n[bold cyan]Installing {component.name}...[/bold cyan]\n")

    deploys = files("videonode_sbc_config.deploys")

    for script in component.scripts:
        console.print(f"[dim]Running {script}...[/dim]")
        path = deploys.joinpath(script)
        cmd = ["pyinfra", "@local", str(path)]
        if "kernel_overlays" in script and platform.board:
            cmd.extend(["--data", f"board={platform.board}"])
        result = subprocess.run(cmd)
        if result.returncode != 0:
            console.print(
                f"[red]Script {script} failed with code {result.returncode}[/red]"
            )
            console.print("\n[dim]Press any key to continue...[/dim]")
            readchar.readkey()
            return

    console.print(f"\n[green]{component.name} installed successfully[/green]")
    console.print("\n[dim]Press any key to continue...[/dim]")
    readchar.readkey()


def render_dashboard(
    platform: Platform,
    results: list[CheckResult],
    verbose: bool = False,
) -> None:
    console = Console()
    console.print(_build_platform_panel(platform))
    console.print()

    table = Table(show_header=True, header_style="bold")
    table.add_column("Check", style="cyan", min_width=20)
    table.add_column("Status", justify="center", width=6)
    table.add_column("Details", min_width=20)

    for check in results:
        details = check.message
        if verbose and check.remediation and check.status == CheckStatus.FAIL:
            details += f" [dim]({check.remediation})[/dim]"
        table.add_row(check.name, STATUS_ICONS[check.status], details)

    console.print(table)
    console.print()

    passed = sum(1 for c in results if c.status == CheckStatus.PASS)
    failed = sum(1 for c in results if c.status == CheckStatus.FAIL)
    skipped = sum(1 for c in results if c.status == CheckStatus.SKIP)

    if failed == 0:
        summary = "[green bold]ALL CHECKS PASSED[/green bold]"
        border_style = "green"
    else:
        summary = f"[red bold]{failed} CHECKS FAILED[/red bold]"
        border_style = "red"

    stats = f"Passed: {passed} | Failed: {failed}"
    if skipped > 0:
        stats += f" | Skipped: {skipped}"

    console.print(
        Panel(f"{summary}\n{stats}", title="Summary", border_style=border_style)
    )


def run_interactive(platform: Platform) -> None:
    console = Console()
    components = get_components_for_platform(platform.is_rockchip, platform.is_armbian)
    component_map = {c.key: c for c in components}

    while True:
        console.clear()
        results = run_all_checks(platform)

        console.print(_build_platform_panel(platform))
        console.print()

        if components:
            console.print(_build_components_table(components, results))
            console.print()
            console.print(_build_system_info_table(results, components))
        else:
            table = Table(show_header=True, header_style="bold")
            table.add_column("Check", style="cyan", min_width=20)
            table.add_column("Status", justify="center", width=6)
            table.add_column("Details", min_width=20)
            for check in results:
                table.add_row(check.name, STATUS_ICONS[check.status], check.message)
            console.print(table)

        console.print()
        console.print(_build_footer(components))

        try:
            key = readchar.readkey()
        except KeyboardInterrupt:
            console.print()
            sys.exit(0)

        if key in ("q", "Q", "\x03"):
            console.print()
            sys.exit(0)

        if key in component_map:
            _run_install(component_map[key], platform, console)
