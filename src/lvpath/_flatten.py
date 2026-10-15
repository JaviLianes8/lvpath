"""The PTH0 binary flattened form of a LabVIEW path.

LabVIEW's ``Flatten To String`` renders a Path value as a small big-endian
container: the ASCII signature ``PTH0``, a u32 length of what follows, a u16
path type, a u16 component count and then one length-prefixed (Pascal) string
per component. NI's flattened-data page shows ``C:\\File`` flattening to::

    50 54 48 30  00 00 00 0B  00 00  00 02  01 43  04 66 69 6C 65

This module is a faithful codec for that container. It keeps the numeric path
type as read, so any flattened path round-trips byte for byte, and it gives no
meaning to a type code that has not been established.
"""

from __future__ import annotations

import struct
from collections.abc import Iterable
from dataclasses import dataclass
from enum import IntEnum

from ._fields import FlatPathError, as_bytes, check_components, check_type

SIGNATURE: bytes = b"PTH0"
"""The four ASCII bytes that open every flattened LabVIEW path."""

_HEADER = struct.Struct(">4sIHH")  # signature, length, path type, count


class FlatPathType(IntEnum):
    """The path type codes, as LabVIEW's ``cintools/extcode.h`` numbers them.

    ``ABSOLUTE`` is also the code of NI's ``C:\\File`` example; ``RELATIVE`` is
    the code of the relative links LabVIEW 2026 stores in its own VI files, where
    an empty component means one level up; ``NOT_A_PATH`` is the code of the
    ``<Not A Path>`` record in LabVIEW 2026's ``resource/labview.rsc``. ``UNC``
    is named but its component layout is not decoded. Other codes are kept as
    read and never interpreted.

    >>> [member.name for member in FlatPathType]
    ['ABSOLUTE', 'RELATIVE', 'NOT_A_PATH', 'UNC']
    """

    __module__ = "lvpath"

    ABSOLUTE = 0
    RELATIVE = 1
    NOT_A_PATH = 2
    UNC = 3


@dataclass(frozen=True)
class FlatPath:
    """A parsed PTH0 flattened path: the raw path type and its components.

    ``path_type`` is the u16 read from the stream, so a path with an
    un-interpreted type code still round-trips through :meth:`to_bytes`.
    ``components`` is a tuple of the Pascal-string parts in order, each ASCII and
    at most 255 characters. Values outside
    those limits raise :class:`FlatPathError`, values of the wrong type
    ``TypeError``.

    >>> FlatPath(path_type=1, components=("", "sub.vi"))
    FlatPath(path_type=1, components=('', 'sub.vi'))
    """

    __module__ = "lvpath"

    path_type: int
    components: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "path_type", check_type(self.path_type))
        object.__setattr__(self, "components", check_components(self.components))

    def __setstate__(self, state: dict[str, object]) -> None:
        # Unpickling skips __post_init__; check the fields here too, so a pickle
        # written by 0.3.1 (a list of components, an enum type) loads normalised.
        object.__setattr__(self, "path_type", check_type(state.get("path_type")))
        object.__setattr__(self, "components", check_components(state.get("components")))

    @property
    def is_absolute(self) -> bool:
        """Whether the path type is the absolute code (``0``).

        >>> FlatPath(0, ("C", "file")).is_absolute
        True
        """
        return self.path_type == FlatPathType.ABSOLUTE

    @property
    def is_relative(self) -> bool:
        """Whether the path type is the relative code (``1``).

        >>> FlatPath(1, ("a",)).is_relative
        True
        """
        return self.path_type == FlatPathType.RELATIVE

    def to_bytes(self) -> bytes:
        """Serialize this path to its PTH0 flattened byte string.

        >>> FlatPath(0, ("C", "file")).to_bytes().hex()
        '505448300000000b0000000201430466696c65'
        """
        body = bytearray(struct.pack(">HH", self.path_type, len(self.components)))
        for component in self.components:
            body.append(len(component))
            body += component.encode("ascii")
        return struct.pack(">4sI", SIGNATURE, len(body)) + bytes(body)

    @classmethod
    def from_bytes(cls, data: bytes | bytearray | memoryview) -> FlatPath:
        """Parse a PTH0 flattened byte string into a :class:`FlatPath`.

        >>> FlatPath.from_bytes(bytes.fromhex("505448300000000b0000000201430466696c65"))
        FlatPath(path_type=0, components=('C', 'file'))
        """
        raw = as_bytes(data)
        if len(raw) < _HEADER.size:
            raise FlatPathError(
                f"flattened path is too short: {len(raw)} bytes, need at least {_HEADER.size}"
            )
        signature, total, path_type, count = _HEADER.unpack_from(raw)
        if signature != SIGNATURE:
            raise FlatPathError(f"bad signature: expected {SIGNATURE!r}, got {signature!r}")
        body = raw[8:]
        if len(body) != total:
            raise FlatPathError(f"declared length {total} does not match body of {len(body)} bytes")
        components, offset = _read_components(body, count)
        if offset != len(body):
            raise FlatPathError(f"{len(body) - offset} trailing byte(s) after {count} component(s)")
        return cls(path_type=path_type, components=tuple(components))


def build_flat_path(path_type: int, components: Iterable[str]) -> bytes:
    """Build PTH0 bytes from a numeric path type and its components.

    >>> build_flat_path(1, ["", "x.vi"]).hex()
    '505448300000000a000100020004782e7669'
    """
    return FlatPath(path_type=path_type, components=components).to_bytes()  # type: ignore[arg-type]


def parse_flat_path(data: bytes | bytearray | memoryview) -> FlatPath:
    """Parse PTH0 bytes into a typed :class:`FlatPath` result.

    >>> parse_flat_path(bytes.fromhex("505448300000000400020000"))
    FlatPath(path_type=2, components=())
    """
    return FlatPath.from_bytes(data)


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
        chunk = body[offset:end]
        if not chunk.isascii():
            raise FlatPathError(f"component {index} is not ASCII")
        components.append(chunk.decode("ascii"))
        offset = end
    return components, offset
