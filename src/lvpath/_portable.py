"""LabVIEW's portable path string form and native ``pathlib`` paths.

When LabVIEW writes a path value into a configuration file or a project file it
uses a platform-independent text form instead of the host's native one:

- a Windows drive becomes a leading single-letter component, so ``C:\\DIR1\\DIR2``
  is stored as ``/C/DIR1/DIR2`` and a bare drive ``C:\\`` as ``/C``;
- a UNC share keeps a leading double slash, ``//server/share/dir``;
- every separator is a forward slash, so relative paths read ``../builds/app``;
- a POSIX absolute path (Linux, macOS) is already in this form;
- the empty string is ``<Not A Path>``.

This module converts that form to and from ``PureWindowsPath`` and
``PurePosixPath``. Values with no faithful counterpart on the target platform
(a POSIX absolute path read on Windows, a drive-relative ``C:file``, a rooted
path with no drive, a ``\\\\?\\`` device path) raise :class:`PortablePathError`
instead of being turned into a different path.
"""

from __future__ import annotations

import re
from pathlib import PurePath, PurePosixPath, PureWindowsPath

from ._kinds import NotAPathError
from ._platform import Platform, flavor, resolve

_PORTABLE_DRIVE = re.compile(r"^/([A-Za-z])(?:/(.*))?$", re.DOTALL)
_MALFORMED_DRIVE = re.compile(r"^/[A-Za-z][:\\]")
_DEVICE_PREFIXES = ("\\\\?\\", "\\\\.\\")


class PortablePathError(ValueError):
    """Raised when a path has no faithful equivalent in the requested form.

    The message names the value and why it cannot be converted, for example a
    POSIX absolute path read as a Windows path or a drive-relative ``C:file``.
    """


def from_portable_path(text: str, *, platform: Platform | str | None = None) -> PurePath:
    """Parse LabVIEW's portable path string into a ``PurePath`` for ``platform``.

    On Windows ``/C/DIR1/DIR2`` becomes ``PureWindowsPath('C:/DIR1/DIR2')``,
    ``//server/share/dir`` becomes a UNC path and ``../a/b`` a relative path.
    A value already written in native Windows form (``C:\\DIR1``) is accepted
    as is. On POSIX the portable form is already native and is parsed directly.

    Raises :class:`NotAPathError` for the empty ``<Not A Path>`` value and
    :class:`PortablePathError` for a value with no Windows equivalent.
    """
    if text == "":
        raise NotAPathError("LabVIEW not-a-path has no OS path")
    if resolve(platform) is Platform.POSIX:
        return PurePosixPath(text)
    match = _PORTABLE_DRIVE.fullmatch(text)
    if match:
        drive, rest = match.groups()
        return PureWindowsPath(f"{drive}:\\{rest or ''}")
    if _MALFORMED_DRIVE.match(text):
        raise PortablePathError(f"{text!r} has a malformed drive component, expected /C/...")
    if text.startswith("/") and not text.startswith(("//", "/\\")):
        raise PortablePathError(f"{text!r} is a POSIX absolute path with no Windows equivalent")
    pure = PureWindowsPath(text)
    _check_windows(pure, text)
    return pure


def to_portable_path(
    os_path: PurePath | str | None, *, platform: Platform | str | None = None
) -> str:
    """Serialize a native path into LabVIEW's portable path string.

    ``C:\\DIR1\\DIR2`` becomes ``/C/DIR1/DIR2``, ``\\\\server\\share\\dir``
    becomes ``//server/share/dir`` and a relative path joins its parts with
    forward slashes. ``None`` or ``""`` becomes the ``<Not A Path>`` value ``""``;
    an empty ``PurePath`` is pathlib's current directory and becomes ``"."``.

    A ``str`` is parsed with the flavor of ``platform`` (default: the running
    operating system). A ``PurePath`` keeps its own flavor; when ``platform``
    names the other flavor, only a relative path may be carried across.

    Raises :class:`PortablePathError` for a Windows path with no portable form.
    """
    if os_path is None or os_path == "":
        return ""
    original = os_path if isinstance(os_path, str) else str(os_path)
    pure = _as_pure(os_path, platform)
    if isinstance(pure, PureWindowsPath):
        return _windows_to_portable(pure, original)
    return str(pure)


def _as_pure(os_path: PurePath | str, platform: Platform | str | None) -> PurePath:
    if isinstance(os_path, str):
        return flavor(resolve(platform))(os_path)
    if platform is None:
        return os_path
    target = flavor(resolve(platform))
    if isinstance(os_path, target):
        return os_path
    if os_path.anchor:
        raise PortablePathError(
            f"cannot carry the anchored path {str(os_path)!r} to the {target.__name__} flavor"
        )
    if target is PureWindowsPath and any("\\" in part for part in os_path.parts):
        raise PortablePathError(
            f"a component of {str(os_path)!r} contains a backslash, a Windows separator"
        )
    return target(*os_path.parts)


def _windows_to_portable(pure: PureWindowsPath, original: str) -> str:
    _check_windows(pure, original)
    if not pure.drive:
        return "/".join(pure.parts) or "."
    rest = "/".join(pure.parts[1:])
    if pure.drive.startswith("\\\\"):
        head = "//" + pure.drive[2:].replace("\\", "/")
    else:
        head = "/" + pure.drive[0]
    return f"{head}/{rest}" if rest else head


def _check_windows(pure: PureWindowsPath, original: str) -> None:
    # The UNC and device forms are judged on the text itself: pathlib parses an
    # incomplete UNC prefix differently across Python versions.
    text = original.replace("/", "\\")
    if text.startswith(_DEVICE_PREFIXES):
        raise PortablePathError(f"{original!r} is a device path with no portable form")
    if text.startswith("\\\\"):
        server, _, rest = text[2:].partition("\\")
        if not server or not rest.partition("\\")[0] or not pure.drive.startswith("\\\\"):
            raise PortablePathError(f"{original!r} is not a //server/share UNC path")
        return
    if pure.drive and not pure.root:
        raise PortablePathError(f"{original!r} is drive-relative and has no portable form")
    if pure.root and not pure.drive:
        raise PortablePathError(f"{original!r} is rooted without a drive or UNC share")
