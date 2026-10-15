"""Target platform selection and the matching pure-path flavor."""

from __future__ import annotations

import os
from enum import Enum
from pathlib import PurePath, PurePosixPath, PureWindowsPath

from ._text import quote, type_name


class Platform(Enum):
    """A LabVIEW host platform whose path convention a string follows.

    Every ``platform`` argument takes a member, its value (``"windows"`` or
    ``"posix"``, in any letter case) or ``None`` for the running system.

    >>> Platform("windows") is Platform.WINDOWS
    True
    >>> [member.value for member in Platform]
    ['windows', 'posix']
    """

    WINDOWS = "windows"
    POSIX = "posix"


def current_platform() -> Platform:
    """The platform convention of the operating system running this code."""
    return Platform.WINDOWS if os.name == "nt" else Platform.POSIX


def resolve(platform: Platform | str | None) -> Platform:
    """Normalise the ``platform`` argument, defaulting to the current OS.

    >>> resolve("POSIX")
    <Platform.POSIX: 'posix'>
    """
    if platform is None:
        return current_platform()
    if isinstance(platform, Platform):
        return platform
    if not isinstance(platform, str):
        raise TypeError(f"platform must be a Platform, a str or None, not {type_name(platform)}")
    name = str.__str__(platform).lower()
    for member in Platform:
        if member.value == name:
            return member
    raise ValueError(f"unknown platform: {quote(platform)}, expected 'windows' or 'posix'")


def flavor(platform: Platform) -> type[PurePath]:
    """The ``PurePath`` subclass that parses and renders ``platform`` paths."""
    return PureWindowsPath if platform is Platform.WINDOWS else PurePosixPath
