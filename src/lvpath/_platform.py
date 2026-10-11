"""Target platform selection and the matching pure-path flavor."""

from __future__ import annotations

import os
from enum import Enum
from pathlib import PurePath, PurePosixPath, PureWindowsPath


class Platform(Enum):
    """A LabVIEW host platform whose path convention a string follows."""

    WINDOWS = "windows"
    POSIX = "posix"


def current_platform() -> Platform:
    """The platform convention of the operating system running this code."""
    return Platform.WINDOWS if os.name == "nt" else Platform.POSIX


def resolve(platform: Platform | str | None) -> Platform:
    """Normalise the ``platform`` argument, defaulting to the current OS."""
    if platform is None:
        return current_platform()
    if isinstance(platform, Platform):
        return platform
    try:
        return Platform(platform.lower())
    except ValueError:
        raise ValueError(f"unknown platform: {platform!r}") from None


def flavor(platform: Platform) -> type[PurePath]:
    """The ``PurePath`` subclass that parses and renders ``platform`` paths."""
    return PureWindowsPath if platform is Platform.WINDOWS else PurePosixPath
