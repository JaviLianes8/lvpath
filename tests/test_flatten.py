from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath

import pytest

from lvpath import (
    FlatPath,
    FlatPathError,
    FlatPathType,
    build_flat_path,
    from_flat_path,
    parse_flat_path,
    to_flat_path,
)

# The NI documented flattened form of the absolute path C:\File. The bytes are
# authoritative; they spell "file" in lower case even though the prose capitalises it.
GOLDEN = bytes.fromhex("505448300000000b0000000201430466696c65")


def test_golden_parses_to_absolute_two_components() -> None:
    flat = parse_flat_path(GOLDEN)
    assert flat == FlatPath(path_type=0, components=("C", "file"))
    assert flat.is_absolute
    assert not flat.is_relative
    assert flat.path_type == FlatPathType.ABSOLUTE


def test_golden_round_trips_byte_exact() -> None:
    assert parse_flat_path(GOLDEN).to_bytes() == GOLDEN


def test_build_matches_the_golden_bytes() -> None:
    assert build_flat_path(0, ("C", "file")) == GOLDEN


def test_relative_round_trips_through_the_codec() -> None:
    flat = FlatPath(path_type=int(FlatPathType.RELATIVE), components=("data", "run.txt"))
    assert FlatPath.from_bytes(flat.to_bytes()) == flat
    assert flat.is_relative


def test_empty_component_list_round_trips() -> None:
    flat = FlatPath(path_type=1, components=())
    assert FlatPath.from_bytes(flat.to_bytes()) == flat


def test_unknown_type_code_round_trips_faithfully() -> None:
    # A type code the library does not interpret is still preserved exactly.
    flat = FlatPath(path_type=7, components=("x",))
    restored = FlatPath.from_bytes(flat.to_bytes())
    assert restored == flat
    assert not restored.is_absolute and not restored.is_relative


def test_bad_signature_is_rejected() -> None:
    corrupt = b"XXXX" + GOLDEN[4:]
    with pytest.raises(FlatPathError, match="signature"):
        parse_flat_path(corrupt)


def test_short_stream_is_rejected() -> None:
    with pytest.raises(FlatPathError, match="too short"):
        parse_flat_path(b"PTH0")


def test_declared_length_mismatch_is_rejected() -> None:
    corrupt = GOLDEN[:4] + (0xFF).to_bytes(4, "big") + GOLDEN[8:]
    with pytest.raises(FlatPathError, match="declared length"):
        parse_flat_path(corrupt)


def test_component_overrun_is_rejected() -> None:
    # One component claiming 9 bytes in a body that only has a few left.
    body = (0).to_bytes(2, "big") + (1).to_bytes(2, "big") + bytes([9]) + b"ab"
    data = b"PTH0" + len(body).to_bytes(4, "big") + body
    with pytest.raises(FlatPathError, match="overruns"):
        parse_flat_path(data)


def test_non_ascii_component_is_rejected() -> None:
    with pytest.raises(FlatPathError, match="ASCII"):
        FlatPath(path_type=1, components=("caf\u00e9",)).to_bytes()


def test_path_type_out_of_range_is_rejected() -> None:
    with pytest.raises(FlatPathError, match="u16 range"):
        FlatPath(path_type=70000, components=())


def test_golden_decodes_to_a_windows_path() -> None:
    assert from_flat_path(GOLDEN, platform="windows") == PureWindowsPath("C:/file")


def test_windows_absolute_round_trips_via_the_bridge() -> None:
    data = to_flat_path(PureWindowsPath("C:/Users/test"), platform="windows")
    assert from_flat_path(data, platform="windows") == PureWindowsPath("C:/Users/test")


def test_windows_absolute_from_string_matches_golden() -> None:
    assert to_flat_path("C:/file", platform="windows") == GOLDEN


def test_posix_absolute_round_trips_via_the_bridge() -> None:
    data = to_flat_path("/usr/local/bin", platform="posix")
    assert parse_flat_path(data) == FlatPath(path_type=0, components=("usr", "local", "bin"))
    assert from_flat_path(data, platform="posix") == PurePosixPath("/usr/local/bin")


def test_relative_path_round_trips_via_the_bridge() -> None:
    data = to_flat_path("data/logs/run.txt", platform="windows")
    assert parse_flat_path(data).path_type == FlatPathType.RELATIVE
    assert from_flat_path(data, platform="windows") == PureWindowsPath("data/logs/run.txt")


def test_unc_path_is_refused_with_an_honest_error() -> None:
    with pytest.raises(FlatPathError, match="UNC"):
        to_flat_path(r"\\server\share\file", platform="windows")


def test_uninterpretable_type_code_is_refused_by_the_bridge() -> None:
    data = FlatPath(path_type=9, components=("x",)).to_bytes()
    with pytest.raises(FlatPathError, match="no PurePath meaning"):
        from_flat_path(data, platform="windows")
