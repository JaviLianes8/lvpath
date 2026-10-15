"""Checks on the fields of a flattened path and on the bytes it is read from."""

from __future__ import annotations

import operator
from collections.abc import Iterable
from typing import SupportsIndex, cast

from ._text import quote, type_name


class FlatPathError(ValueError):
    """Raised when flattened path bytes or components are malformed or cannot be interpreted.

    The message names the problem: a wrong signature, a truncated stream, a
    declared length that disagrees with the body, a component that overruns the
    buffer or is not ASCII, or a path with no ``PurePath`` meaning.

    >>> from lvpath import parse_flat_path
    >>> parse_flat_path(b"PTH1" + bytes(8))
    Traceback (most recent call last):
    ...
    lvpath.FlatPathError: bad signature: expected b'PTH0', got b'PTH1'
    >>> issubclass(FlatPathError, ValueError)
    True
    """

    __module__ = "lvpath"


def as_bytes(data: object) -> bytes:
    if isinstance(data, str):
        raise TypeError("flattened path data must be bytes-like, not str")
    try:
        view = memoryview(data)  # type: ignore[arg-type]
    except TypeError:
        raise TypeError(f"flattened path data must be bytes-like, not {type_name(data)}") from None
    with view:
        return view.tobytes()


def check_type(path_type: object) -> int:
    if isinstance(path_type, bool) or not hasattr(type(path_type), "__index__"):
        raise TypeError(f"path type must be an integer, not {type_name(path_type)}")
    value = operator.index(cast("SupportsIndex", path_type))
    if not 0 <= value <= 0xFFFF:
        shown = (
            str(value) if -(10**9) < value < 10**9 else f"an integer of {value.bit_length()} bits"
        )
        raise FlatPathError(f"path type out of u16 range: {shown}")
    return int(value)


def check_components(components: object) -> tuple[str, ...]:
    if isinstance(components, (str, bytes, bytearray, memoryview)):
        raise TypeError(f"components must be an iterable of str, not {type_name(components)}")
    if not isinstance(components, Iterable):
        raise TypeError(f"components must be an iterable of str, not {type_name(components)}")
    parts: list[str] = []
    for component in components:
        if not isinstance(component, str):
            raise TypeError(f"each component must be a str, not {type_name(component)}")
        if len(parts) == 0xFFFF:
            raise FlatPathError("too many components to flatten: more than 65535")
        if not str.isascii(component):
            raise FlatPathError(f"component is not ASCII: {quote(component)}")
        if len(component) > 0xFF:
            raise FlatPathError(f"component too long to flatten: {len(component)} bytes")
        parts.append(str.__str__(component))
    return tuple(parts)
