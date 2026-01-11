"""Rich dashboard rendering for status checks."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from videonode_sbc_config.deploys.verify import CheckResult, CheckStatus
from videonode_sbc_config.platform import Platform

STATUS_ICONS = {
    CheckStatus.PASS: "[green]OK[/green]",
    CheckStatus.FAIL: "[red]FAIL[/red]",
    CheckStatus.INFO: "[blue]INFO[/blue]",
    CheckStatus.SKIP: "[dim]SKIP[/dim]",
}


def render_dashboard(
    platform: Platform,
    results: list[CheckResult],
    verbose: bool = False,
) -> None:
    """Render status dashboard to terminal."""
    console = Console()

    # Platform panel
    platform_info = f"Board:   {platform.board or '(unknown)'}\n"
    platform_info += (
        f"SBC:     {platform.sbc_family.name}/{platform.sbc_model.name}\n"
        f"OS:      {platform.os_type.name}"
    )
    if platform.os_version:
        platform_info += f" {platform.os_version}"
    platform_info += f"\nKernel:  {platform.kernel_version}"

    console.print(Panel(platform_info, title="Platform"))
    console.print()

    # Checks table
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

    # Summary
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
