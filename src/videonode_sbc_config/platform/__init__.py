"""Platform detection for SBC configuration."""

from .detect import detect_platform
from .types import OSType, Platform, SBCFamily, SBCModel

__all__ = ["detect_platform", "OSType", "Platform", "SBCFamily", "SBCModel"]
