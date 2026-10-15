"""Bridge the PTH0 flattened form to and from ``pathlib.PurePath``.

Two path types are interpreted: absolute (``0``) and relative (``1``). In both,
an empty component means one level up, ``..`` in text: LabVIEW 2026 stores the
relative links inside its own VI files that way. An absolute Windows path starts
with its drive letter, without the colon; an absolute POSIX path lists the parts
after the root. Anything else (another type code, a symbolic ``<vilib>`` prefix,
a component that would read as a separator, a UNC share) raises
:class:`FlatPathError`; the low-level :class:`FlatPath` codec still keeps such
bytes exactly.
"""

from __future__ import annotations

import string
from pathlib import PurePath, PurePosixPath, PureWindowsPath

from ._coerce import as_pure
from ._flatten import FlatPath, FlatPathError, FlatPathType, parse_flat_path
from ._platform import Platform, flavor, resolve
from ._text import quote

_LETTERS = frozenset(string.ascii_letters)


def to_flat_path(os_path: PurePath | str, *, platform: Platform | str | None = None) -> bytes:
    """Encode an OS path into its PTH0 flattened byte string.

    A ``str`` is parsed with the flavor of ``platform`` (default: the running
    system); a ``PurePath`` keeps its own flavor unless ``platform`` names the
    other one, which only a relative path may cross. ``..`` becomes an empty
    component. UNC, rooted driveless and drive-relative Windows paths, POSIX
    paths starting with ``//`` and components that are not ASCII or longer than
    255 characters raise :class:`FlatPathError`.

    >>> to_flat_path("C:\\\\file", platform="windows").hex()
    '505448300000000b0000000201430466696c65'
    >>> parse_flat_path(to_flat_path("../sub.vi", platform="posix"))
    FlatPath(path_type=1, components=('', 'sub.vi'))
    """
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
    :class:`FlatPathError` for malformed bytes and for any path that has no
    faithful ``PurePath`` on the target, listed in the module notes; use
    :func:`lvpath.parse_flat_path` to inspect such a path instead.

    >>> from_flat_path(bytes.fromhex("505448300000000b0000000201430466696c65"), platform="windows")
    PureWindowsPath('C:/file')
    >>> from_flat_path(FlatPath(1, ("", "", "lib.lvlib")).to_bytes(), platform="posix")
    PurePosixPath('../../lib.lvlib')
    """
    flat = parse_flat_path(data)
    target = flavor(resolve(platform))
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
