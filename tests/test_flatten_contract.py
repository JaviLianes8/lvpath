"""The complete promise of the flattened codec against the NI golden vector.

This asserts every documented field of the ``PTH0`` container at once, for the
one example NI publishes (the absolute path ``C:\\File``), and proves the
byte-exact round trip in both directions. If any field of the format drifts, this
single test fails.
"""

from __future__ import annotations

import struct

from lvpath import FlatPath, FlatPathType, from_flat_path, parse_flat_path, to_flat_path

# NI's documented flattened bytes for the absolute path C:\File (big-endian).
GOLDEN = bytes.fromhex("505448300000000b0000000201430466696c65")


def test_golden_vector_has_every_documented_field() -> None:
    signature, total = struct.unpack_from(">4sI", GOLDEN, 0)
    path_type, count = struct.unpack_from(">HH", GOLDEN, 8)
    assert signature == b"PTH0"
    assert total == len(GOLDEN) - 8 == 0x0B
    assert path_type == FlatPathType.ABSOLUTE == 0
    assert count == 2
    # Two Pascal strings: 01 'C', then 04 'file'.
    assert GOLDEN[12:14] == bytes([1]) + b"C"
    assert GOLDEN[14:19] == bytes([4]) + b"file"


def test_golden_vector_parses_to_the_expected_result() -> None:
    assert parse_flat_path(GOLDEN) == FlatPath(path_type=0, components=("C", "file"))


def test_golden_vector_round_trips_bytes_to_bytes() -> None:
    assert parse_flat_path(GOLDEN).to_bytes() == GOLDEN


def test_golden_vector_round_trips_through_the_os_bridge() -> None:
    os_path = from_flat_path(GOLDEN, platform="windows")
    assert str(os_path) == "C:\\file"
    assert to_flat_path(os_path, platform="windows") == GOLDEN
