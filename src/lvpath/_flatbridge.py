"""Bridge the PTH0 flattened form to and from ``pathlib.PurePath``.

The path types are those of LabVIEW's ``extcode.h``: absolute (``0``),
relative (``1``), not-a-path (``2``) and UNC (``3``). In absolute and relative
paths an empty component means one level up, ``..`` in text: LabVIEW 2026 stores
the relative links inside its own VI files that way. An absolute Windows path
starts with its drive letter, without the colon; an absolute POSIX path lists the
parts after the root. Not-a-path decodes to :class:`NotAPathError`, as in
:func:`lvpath.to_os_path`. Anything else (a UNC path, whose component layout has
not been checked against LabVIEW output, an unknown type code, a symbolic
``<vilib>`` prefix, a component that would read as a separator) raises
:class:`FlatPathError`; the low-level :class:`FlatPath` codec still keeps such
bytes exactly.
"""

from __future__ import annotations

import string
from pathlib import PurePath, PurePosixPath, PureWindowsPath

from ._coerce import as_pure
from ._fields import FlatPathError
from ._flatten import FlatPath, FlatPathType, parse_flat_path
from ._kinds import NotAPathError
from ._platform import Platform, flavor, resolve
from ._text import quote

_LETTERS = frozenset(string.ascii_letters)


def to_flat_path(
    os_path: PurePath | str | None, *, platform: Platform | str | None = None
) -> bytes:
    """Encode an OS path into its PTH0 flattened byte string.

    A ``str`` is parsed with the flavor of ``platform`` (default: the running
    system); a ``PurePath`` keeps its own flavor unless ``platform`` names the
    other one, which only a relative path may cross. ``..`` becomes an empty
    component. UNC, rooted driveless and drive-relative Windows paths, POSIX
    paths starting with ``//`` and components that are not ASCII or longer than
    255 characters raise :class:`FlatPathError`. ``None`` or ``""`` is LabVIEW's
    ``<Not A Path>`` and encodes as path type ``2`` with no component.

    >>> to_flat_path("", platform="windows").hex()
    '505448300000000400020000'
    >>> to_flat_path("C:\\\\file", platform="windows").hex()
    '505448300000000b0000000201430466696c65'
    >>> parse_flat_path(to_flat_path("../sub.vi", platform="posix"))
    FlatPath(path_type=1, components=('', 'sub.vi'))
    """
    resolve(platform)
    if os_path is None or (isinstance(os_path, str) and str.__len__(os_path) == 0):
        return FlatPath(int(FlatPathType.NOT_A_PATH), ()).to_bytes()
    pure = as_pure(os_path, platform, FlatPathError)
    parts = [("" if part == ".." else part) for part in pure.parts]
    if not pure.anchor:
        return FlatPath(int(FlatPathType.RELATIVE), tuple(parts)).to_bytes()
    if isinstance(pure, PureWindowsPath):
        if pure.drive.startswith("\\\\") or not pure.drive:
            raise FlatPathError(
                f"UNC and driveless rooted paths have no flattened form: {_q(pure)}"
            )
        if not pure.root:
            raise FlatPathError(f"drive-relative paths have no flattened form: {_q(pure)}")
        parts = [pure.drive[0], *parts[1:]]
    else:
        if pure.root != "/":
            raise FlatPathError(f"a POSIX path starting with // has no flattened form: {_q(pure)}")
        parts = parts[1:]
    return FlatPath(int(FlatPathType.ABSOLUTE), tuple(parts)).to_bytes()


def from_flat_path(
    data: bytes | bytearray | memoryview, *, platform: Platform | str | None = None
) -> PurePath:
    """Decode PTH0 flattened bytes into a ``PurePath`` of the platform flavor.

    An empty component becomes ``..``; a relative path with no component is
    ``.``; the absolute path with no component is ``/`` on POSIX. Raises
    :class:`NotAPathError` for not-a-path (type ``2``) and
    :class:`FlatPathError` for malformed bytes and for any path that has no
    faithful ``PurePath`` on the target, listed in the module notes; use
    :func:`lvpath.parse_flat_path` to inspect such a path instead.

    >>> from_flat_path(bytes.fromhex("505448300000000b0000000201430466696c65"), platform="windows")
    PureWindowsPath('C:/file')
    >>> from_flat_path(FlatPath(1, ("", "", "lib.lvlib")).to_bytes(), platform="posix")
    PurePosixPath('../../lib.lvlib')
    """
    target = flavor(resolve(platform))
    flat = parse_flat_path(data)
    if flat.path_type == FlatPathType.NOT_A_PATH:
        raise NotAPathError("LabVIEW not-a-path has no OS path")
    if flat.path_type == FlatPathType.UNC:
        raise FlatPathError("UNC flattened paths are not decoded: their layout is not verified")
    if not (flat.is_absolute or flat.is_relative):
        raise FlatPathError(f"path type {flat.path_type} has no PurePath meaning")
    parts = [_text_part(part, target) for part in flat.components]
    if flat.is_relative:
        return target(*parts) if parts else target(".")
    if parts and parts[0].startswith("<") and parts[0].endswith(">"):
        raise FlatPathError(f"symbolic path prefix {quote(parts[0])} has no PurePath meaning")
    if target is PurePosixPath:
        return PurePosixPath("/", *parts)
    if not parts:
        raise FlatPathError("the absolute path with no component has no Windows PurePath")
    drive, *rest = parts
    if len(drive) != 1 or drive not in _LETTERS:
        raise FlatPathError(f"first component {quote(drive)} is not a Windows drive letter")
    return PureWindowsPath(f"{drive}:\\", *rest)


def _text_part(part: str, target: type[PurePath]) -> str:
    if part == "":
        return ".."
    if part in (".", ".."):
        raise FlatPathError(f"component {quote(part)} is not a name LabVIEW writes")
    special = "/\\:" if target is PureWindowsPath else "/"
    if any(char in special for char in part):
        raise FlatPathError(f"component {quote(part)} holds a path separator for this flavor")
    return part


def _q(pure: PurePath) -> str:
    return quote(str(pure))
