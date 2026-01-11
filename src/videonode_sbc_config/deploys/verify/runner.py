"""Subprocess-based check runner."""

import subprocess
from collections.abc import Callable

from .types import CheckResult, CheckStatus


def run_check(
    name: str,
    command: str,
    check_fn: Callable[[str], bool] | None = None,
    pass_msg: str = "",
    fail_msg: str = "",
    remediation: str | None = None,
) -> CheckResult:
    """Run a verification check via subprocess.

    Args:
        name: Display name for the check
        command: Shell command to execute
        check_fn: Function to evaluate result (None = info only)
        pass_msg: Message on pass ("{result}" = use command output)
        fail_msg: Message on fail ("{result}" = use command output)
        remediation: Command/action to fix a failure

    Returns:
        CheckResult with check outcome
    """
    result = subprocess.run(
        ["sh", "-c", command],
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip()

    if check_fn is None:
        return CheckResult(name=name, status=CheckStatus.INFO, message=output)

    passed = check_fn(output)

    if passed:
        msg = pass_msg.replace("{result}", output) if pass_msg else ""
    else:
        msg = fail_msg.replace("{result}", output) if fail_msg else ""

    return CheckResult(
        name=name,
        status=CheckStatus.PASS if passed else CheckStatus.FAIL,
        message=msg,
        remediation=remediation if not passed else None,
    )
