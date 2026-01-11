"""Platform verification framework."""

from videonode_sbc_config.platform import Platform

from .rockchip_armbian import get_checks as get_rockchip_armbian_checks
from .types import CheckResult, CheckStatus

__all__ = ["CheckResult", "CheckStatus", "run_all_checks"]


def run_all_checks(platform: Platform) -> list[CheckResult]:
    """Run verification checks for detected platform."""
    if platform.is_rockchip and platform.is_armbian:
        return get_rockchip_armbian_checks(platform)
    return [CheckResult("Platform", CheckStatus.SKIP, f"Unsupported: {platform}")]
