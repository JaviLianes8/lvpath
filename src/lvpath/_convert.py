"""Conversion between LabVIEW path strings and native OS paths."""

from __future__ import annotations

from pathlib import PurePath

from ._kinds import NotAPathError, PathKind
from ._platform import Platform, flavor, resolve


def path_kind(lv_path: str, *, platform: Platform | str | None = None) -> PathKind:
    """Classify a LabVIEW path string as absolute, relative or not-a-path.

    An empty string is LabVIEW's ``<Not A Path>`` value on every platform.
    """
    if lv_path == "":
        return PathKind.NOT_A_PATH
    pure = flavor(resolve(platform))(lv_path)
    return PathKind.ABSOLUTE if pure.is_absolute() else PathKind.RELATIVE


def to_os_path(lv_path: str, *, platform: Platform | str | None = None) -> PurePath:
    """Parse a LabVIEW path string into a ``PurePath`` of the platform flavor.

    Raises :class:`NotAPathError` for the empty not-a-path value, which has no
    operating-system path. Forward slashes are accepted when parsing a Windows
    path, matching LabVIEW's lenient reader. This reads the host's native text
    form; for the portable form LabVIEW writes into configuration and project
    files (``/C/DIR1/DIR2``) use :func:`lvpath.from_portable_path`.
    """
    if lv_path == "":
        raise NotAPathError("LabVIEW not-a-path has no OS path")
    return flavor(resolve(platform))(lv_path)


def to_lv_path(os_path: PurePath | str | None, *, platform: Platform | str | None = None) -> str:
    """Serialize an OS path into a LabVIEW path string for ``platform``.

    ``None`` or an empty string becomes LabVIEW's not-a-path value (``""``).
    The components of ``os_path`` are rendered with the separators of the
    target platform, so a relative path crosses platforms cleanly.
    """
    if os_path is None or os_path == "":
        return ""
    target = flavor(resolve(platform))
    if isinstance(os_path, str):
        return str(target(os_path))
    return str(target(*os_path.parts))
