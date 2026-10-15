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

from ._coerce import as_pure
from ._kinds import NotAPathError
from ._platform import Platform, resolve
from ._text import quote, type_name

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

    >>> from_portable_path("/C/Program Files (x86)/Arduino", platform="windows")
    PureWindowsPath('C:/Program Files (x86)/Arduino')
    >>> from_portable_path("//server/share/dir", platform="windows")
    PureWindowsPath('//server/share/dir')
    >>> from_portable_path("/home/lvuser/natinst/bin", platform="posix")
    PurePosixPath('/home/lvuser/natinst/bin')
    """
    if not isinstance(text, str):
        raise TypeError(f"a portable path string must be a str, not {type_name(text)}")
    text = str.__str__(text)
    if text == "":
        raise NotAPathError("LabVIEW not-a-path has no OS path")
    if resolve(platform) is Platform.POSIX:
        return PurePosixPath(text)
    match = _PORTABLE_DRIVE.fullmatch(text)
    if match:
        drive, rest = match.groups()
        return PureWindowsPath(f"{drive}:\\{rest or ''}")
    if _MALFORMED_DRIVE.match(text):
        raise PortablePathError(f"{quote(text)} has a malformed drive component, expected /C/...")
    if text.startswith("/") and not text.startswith(("//", "/\\")):
        raise PortablePathError(
            f"{quote(text)} is a POSIX absolute path with no Windows equivalent"
        )
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

    >>> to_portable_path("C:/DIR1/DIR2", platform="windows")
    '/C/DIR1/DIR2'
    >>> to_portable_path("//server/share/dir", platform="windows")
    '//server/share/dir'
    >>> to_portable_path(None)
    ''
    """
    if os_path is None or (isinstance(os_path, str) and os_path == ""):
        return ""
    original = str.__str__(os_path) if isinstance(os_path, str) else str(os_path)
    pure = as_pure(os_path, platform, PortablePathError)
    if isinstance(pure, PureWindowsPath):
        return _windows_to_portable(pure, original)
    return str(pure)


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
        raise PortablePathError(f"{quote(original)} is a device path with no portable form")
    if text.startswith("\\\\"):
        server, _, rest = text[2:].partition("\\")
        if not server or not rest.partition("\\")[0] or not pure.drive.startswith("\\\\"):
            raise PortablePathError(f"{quote(original)} is not a //server/share UNC path")
        return
    if pure.drive and not pure.root:
        raise PortablePathError(f"{quote(original)} is drive-relative and has no portable form")
    if pure.root and not pure.drive:
        raise PortablePathError(f"{quote(original)} is rooted without a drive or UNC share")
