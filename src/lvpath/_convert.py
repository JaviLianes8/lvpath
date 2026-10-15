"""Conversion between LabVIEW's native path text and ``pathlib`` pure paths."""

from __future__ import annotations

from pathlib import PurePath

from ._coerce import as_pure
from ._kinds import NotAPathError, PathKind
from ._platform import Platform, flavor, resolve
from ._portable import PortablePathError
from ._text import type_name


def path_kind(lv_path: str, *, platform: Platform | str | None = None) -> PathKind:
    """Classify a LabVIEW path string as absolute, relative or not-a-path.

    An empty string is LabVIEW's ``<Not A Path>`` value on every platform. The
    rest follows ``pathlib``: on Windows only a drive with a root or a UNC share
    is absolute, so ``C:file`` and ``\\\\dir`` are relative.

    >>> path_kind("C:\\\\x", platform="windows")
    <PathKind.ABSOLUTE: 'absolute'>
    >>> path_kind("sub/file", platform="posix")
    <PathKind.RELATIVE: 'relative'>
    >>> path_kind("", platform="posix")
    <PathKind.NOT_A_PATH: 'not_a_path'>
    """
    pure = _parse(lv_path, platform)
    if pure is None:
        return PathKind.NOT_A_PATH
    return PathKind.ABSOLUTE if pure.is_absolute() else PathKind.RELATIVE


def to_os_path(lv_path: str, *, platform: Platform | str | None = None) -> PurePath:
    """Parse a LabVIEW path string into a ``PurePath`` of the platform flavor.

    Raises :class:`NotAPathError` for the empty not-a-path value. Forward
    slashes are accepted when parsing a Windows path. This reads the host's
    native text form; for the portable form LabVIEW writes into configuration
    and project files (``/C/DIR1/DIR2``) use :func:`lvpath.from_portable_path`.

    >>> to_os_path("C:\\\\Users\\\\test\\\\data.txt", platform="windows")
    PureWindowsPath('C:/Users/test/data.txt')
    >>> to_os_path("/usr/local/bin", platform="posix")
    PurePosixPath('/usr/local/bin')
    """
    pure = _parse(lv_path, platform)
    if pure is None:
        raise NotAPathError("LabVIEW not-a-path has no OS path")
    return pure


def to_lv_path(os_path: PurePath | str | None, *, platform: Platform | str | None = None) -> str:
    """Serialize an OS path into a LabVIEW path string.

    ``None`` or ``""`` becomes LabVIEW's not-a-path value (``""``). A ``str`` is
    parsed with the flavor of ``platform`` (default: the running system); a
    ``PurePath`` keeps its own flavor unless ``platform`` names the other one,
    which only a relative path may cross (else :class:`PortablePathError`).

    >>> to_lv_path("logs/run.txt", platform="windows")
    'logs\\\\run.txt'
    >>> from pathlib import PureWindowsPath
    >>> to_lv_path(PureWindowsPath("reports\\\\q1.txt"), platform="posix")
    'reports/q1.txt'
    >>> to_lv_path(None)
    ''
    """
    resolve(platform)
    if os_path is None or (isinstance(os_path, str) and os_path == ""):
        return ""
    return str(as_pure(os_path, platform, PortablePathError))


def _parse(lv_path: object, platform: Platform | str | None) -> PurePath | None:
    target = flavor(resolve(platform))
    if isinstance(lv_path, PurePath):
        return target(lv_path)
    if not isinstance(lv_path, str):
        raise TypeError(f"a LabVIEW path string must be a str, not {type_name(lv_path)}")
    if lv_path == "":
        return None
    return target(str.__str__(lv_path))
