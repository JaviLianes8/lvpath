"""The PTH0 binary flattened form of a LabVIEW path.

LabVIEW's ``Flatten To String`` renders a Path value as a small big-endian
container: the ASCII signature ``PTH0``, a u32 total length, a u16 path type, a
u16 component count and then one length-prefixed (Pascal) string per component.
The absolute path documented by NI as ``C:\\File`` flattens to::

    50 54 48 30  00 00 00 0B  00 00  00 02  01 43  04 66 69 6C 65

This module is a faithful codec for that container. It keeps the numeric path
type as read so any flattened path round-trips byte for byte, and it never
invents a meaning for a type code the NI documentation does not state.
"""

from __future__ import annotations

import struct
from collections.abc import Iterable
from dataclasses import dataclass
from enum import IntEnum

SIGNATURE: bytes = b"PTH0"
"""The four ASCII bytes that open every flattened LabVIEW path."""

_HEADER = struct.Struct(">4sIHH")  # signature, total length, path type, count


class FlatPathType(IntEnum):
    """The path type codes documented and verifiable from the NI example.

    Only these two are stated by the public documentation. UNC and the empty /
    not-a-path forms carry their own codes that the documentation does not give,
    so they are deliberately absent here rather than guessed.
    """

    ABSOLUTE = 0
    RELATIVE = 1


class FlatPathError(ValueError):
    """Raised when flattened path bytes are malformed or cannot be interpreted.

    The message names the problem: a wrong signature, a truncated stream, a
    declared length that disagrees with the body, a component that overruns the
    buffer, or a path type with no documented meaning.
    """


@dataclass(frozen=True)
class FlatPath:
    """A parsed PTH0 flattened path: the raw path type and its components.

    ``path_type`` is kept as the integer read from the stream, so a flattened
    path with an un-interpreted type code still round-trips through
    :meth:`to_bytes` byte for byte. ``components`` are the decoded Pascal-string
    parts in order.
    """

    path_type: int
    components: tuple[str, ...]

    def __post_init__(self) -> None:
        if not 0 <= self.path_type <= 0xFFFF:
            raise FlatPathError(f"path type out of u16 range: {self.path_type}")
        if len(self.components) > 0xFFFF:
            raise FlatPathError(f"too many components to flatten: {len(self.components)}")

    @property
    def is_absolute(self) -> bool:
        """Whether the path type is the documented absolute code (``0``)."""
        return self.path_type == FlatPathType.ABSOLUTE

    @property
    def is_relative(self) -> bool:
        """Whether the path type is the documented relative code (``1``)."""
        return self.path_type == FlatPathType.RELATIVE

    def to_bytes(self) -> bytes:
        """Serialize this path to its PTH0 flattened byte string."""
        body = bytearray(struct.pack(">HH", self.path_type, len(self.components)))
        for component in self.components:
            encoded = _encode_component(component)
            body.append(len(encoded))
            body += encoded
        return struct.pack(">4sI", SIGNATURE, len(body)) + bytes(body)

    @classmethod
    def from_bytes(cls, data: bytes) -> FlatPath:
        """Parse a PTH0 flattened byte string into a :class:`FlatPath`."""
        if len(data) < _HEADER.size:
            raise FlatPathError(
                f"flattened path is too short: {len(data)} bytes, need at least {_HEADER.size}"
            )
        signature, total, path_type, count = _HEADER.unpack_from(data)
        if signature != SIGNATURE:
            raise FlatPathError(f"bad signature: expected {SIGNATURE!r}, got {signature!r}")
        body = data[8:]
        if len(body) != total:
            raise FlatPathError(f"declared length {total} does not match body of {len(body)} bytes")
        components, offset = _read_components(body, count)
        if offset != len(body):
            raise FlatPathError(f"{len(body) - offset} trailing byte(s) after {count} component(s)")
        return cls(path_type=path_type, components=tuple(components))


def build_flat_path(path_type: int, components: Iterable[str]) -> bytes:
    """Build PTH0 bytes from a numeric path type and its components."""
    return FlatPath(path_type=path_type, components=tuple(components)).to_bytes()


def parse_flat_path(data: bytes) -> FlatPath:
    """Parse PTH0 bytes into a typed :class:`FlatPath` result."""
    return FlatPath.from_bytes(data)


def _encode_component(component: str) -> bytes:
    try:
        encoded = component.encode("ascii")
    except UnicodeEncodeError as error:
        raise FlatPathError(f"component is not ASCII: {component!r}") from error
    if len(encoded) > 0xFF:
        raise FlatPathError(f"component too long to flatten: {len(encoded)} bytes")
    return encoded


def _read_components(body: bytes, count: int) -> tuple[list[str], int]:
    components: list[str] = []
    offset = 4  # past the path type and count already read from the header
    for index in range(count):
        if offset >= len(body):
            raise FlatPathError(f"stream ends before component {index} length byte")
        length = body[offset]
        offset += 1
        end = offset + length
        if end > len(body):
            raise FlatPathError(f"component {index} of {length} bytes overruns the buffer")
        components.append(body[offset:end].decode("ascii"))
        offset = end
    return components, offset
