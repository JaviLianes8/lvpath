"""Bridge the PTH0 flattened form to and from ``pathlib.PurePath``.

Only the two documented path type codes are interpreted here: absolute (``0``)
and relative (``1``). UNC, driveless and empty / not-a-path forms carry type
codes the NI documentation does not state, so they are refused with a clear
error rather than guessed. The low-level :mod:`lvpath._flatten` codec still
round-trips their raw bytes faithfully.
"""

from __future__ import annotations

from pathlib import PurePath, PurePosixPath, PureWindowsPath

from ._flatten import FlatPath, FlatPathError, FlatPathType, parse_flat_path
from ._platform import Platform, flavor, resolve


def to_flat_path(os_path: PurePath | str, *, platform: Platform | str | None = None) -> bytes:
    """Encode an OS path into its PTH0 flattened byte string.

    Absolute Windows paths store the drive letter without its colon as the first
    component (matching NI's ``C:\\File`` example); absolute POSIX paths store the
    components after the leading root. UNC, driveless and not-a-path forms are
    refused because their flattened type codes are not documented.
    """
    target = flavor(resolve(platform))
    pure = target(os_path) if isinstance(os_path, str) else target(*os_path.parts)
    if pure.is_absolute():
        return _encode_absolute(pure, target).to_bytes()
    if pure.drive:
        raise FlatPathError(f"drive-relative paths have no documented flattened form: {pure}")
    return FlatPath(path_type=int(FlatPathType.RELATIVE), components=pure.parts).to_bytes()


def from_flat_path(data: bytes, *, platform: Platform | str | None = None) -> PurePath:
    """Decode PTH0 flattened bytes into a ``PurePath`` of the platform flavor.

    Raises :class:`FlatPathError` for a path type with no documented PurePath
    meaning, so an un-interpretable flattened path is reported rather than
    silently reconstructed. Use :func:`lvpath.parse_flat_path` to inspect its raw
    type and components instead.
    """
    flat = parse_flat_path(data)
    target = flavor(resolve(platform))
    if flat.is_relative:
        return target(*flat.components) if flat.components else target(".")
    if flat.is_absolute:
        return _decode_absolute(flat, target)
    raise FlatPathError(f"path type {flat.path_type} has no documented PurePath meaning")


def _encode_absolute(pure: PurePath, target: type[PurePath]) -> FlatPath:
    if target is PureWindowsPath:
        drive = pure.drive
        if drive.startswith("\\\\") or not drive:
            raise FlatPathError(f"UNC and driveless absolute paths are not supported: {pure}")
        components = (drive.rstrip(":"), *pure.parts[1:])
    else:
        components = pure.parts[1:]
    return FlatPath(path_type=int(FlatPathType.ABSOLUTE), components=components)


def _decode_absolute(flat: FlatPath, target: type[PurePath]) -> PurePath:
    if target is PureWindowsPath:
        if not flat.components:
            raise FlatPathError("absolute Windows flattened path has no drive component")
        drive, *rest = flat.components
        return PureWindowsPath(f"{drive}:\\", *rest)
    return PurePosixPath("/", *flat.components)
