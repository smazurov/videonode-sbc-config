"""Rich dashboard rendering for status checks."""

import subprocess
import sys
from importlib.resources import files

import readchar
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from videonode_sbc_config.deploys.hardware.rockchip.overlays import OVERLAYS
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
) -> tuple[CheckStatus, str]:
    """Compute component status and message.

    Returns (status, message) where status is always INFO for neutral display.
    """
    if component.has_submenu:
        # For overlay submenu, count installed overlays
        installed = sum(
            1
            for r in results
            if r.name.startswith("Overlay:") and r.message == "Installed"
        )
        total = len(OVERLAYS)
        return CheckStatus.INFO, f"{installed}/{total}"

    check_map = {r.name: r for r in results}
    statuses = []
    for check_name in component.checks:
        if check_name in check_map:
            statuses.append(check_map[check_name].status)

    if not statuses:
        return CheckStatus.INFO, "-"

    all_pass = all(s == CheckStatus.PASS for s in statuses)
    return CheckStatus.INFO, "Installed" if all_pass else "Not installed"


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
    table.add_column("Status", justify="center", width=14)
    table.add_column("Description", min_width=20)

    for comp in components:
        _status, message = _compute_component_status(comp, results)
        if message == "Installed":
            status_text = "[green]Installed[/green]"
        else:
            status_text = f"[dim]{message}[/dim]"
        table.add_row(
            f"[{comp.key}]",
            comp.name,
            status_text,
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
        # Skip component checks and overlay checks (handled by submenu)
        if check.name in component_check_names:
            continue
        if check.name.startswith("Overlay:"):
            continue
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


def _run_overlay_submenu(platform: Platform, console: Console) -> None:
    """Show overlay selection submenu."""
    deploys = files("videonode_sbc_config.deploys")

    while True:
        console.clear()
        results = run_all_checks(platform)

        console.print(Panel("Select an overlay to install", title="Kernel Overlays"))
        console.print()

        table = Table(show_header=True, header_style="bold", box=None)
        table.add_column("#", style="cyan", width=3)
        table.add_column("Overlay", min_width=20)
        table.add_column("Status", justify="center", width=14)
        table.add_column("Description", min_width=30)

        overlay_map: dict[str, str] = {}
        for i, overlay in enumerate(OVERLAYS, 1):
            key = str(i)
            overlay_map[key] = overlay.id

            # Find status from results
            check_name = f"Overlay: {overlay.name}"
            installed = False
            for r in results:
                if r.name == check_name:
                    installed = r.message == "Installed"
                    break

            status_text = "[green]Installed[/green]" if installed else "[dim]Not installed[/dim]"
            table.add_row(
                f"[{key}]",
                overlay.name,
                status_text,
                overlay.description,
            )

        console.print(table)
        console.print()
        console.print(Text(f"Press 1-{len(OVERLAYS)} to install, b to go back", style="dim"))

        try:
            key = readchar.readkey()
        except KeyboardInterrupt:
            return

        if key in ("b", "B", "\x1b"):  # b or Escape
            return

        if key in overlay_map:
            overlay_id = overlay_map[key]
            console.clear()
            console.print(f"\n[bold cyan]Installing overlay: {overlay_id}...[/bold cyan]\n")

            path = deploys.joinpath("os/armbian/kernel_overlays.py")
            cmd = ["pyinfra", "@local", str(path), "--data", f"overlay_id={overlay_id}"]
            result = subprocess.run(cmd)

            if result.returncode != 0:
                console.print(f"[red]Failed with code {result.returncode}[/red]")
            else:
                console.print("\n[green]Overlay installed (reboot required)[/green]")

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
            comp = component_map[key]
            if comp.has_submenu:
                _run_overlay_submenu(platform, console)
            else:
                _run_install(comp, platform, console)
