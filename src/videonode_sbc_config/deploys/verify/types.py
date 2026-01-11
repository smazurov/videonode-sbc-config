"""Verification check types."""

from dataclasses import dataclass
from enum import Enum


class CheckStatus(Enum):
    """Status of a verification check."""

    PASS = "pass"
    FAIL = "fail"
    INFO = "info"
    SKIP = "skip"


@dataclass
class CheckResult:
    """Result of a single verification check."""

    name: str
    status: CheckStatus
    message: str = ""
    remediation: str | None = None
