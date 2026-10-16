"""Contracts for the behaviour settled in 1.0.0: types, limits, up-levels and safe messages."""

from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath

import pytest

from lvpath import (
    FlatPath,
    FlatPathError,
    Platform,
    PortablePathError,
    build_flat_path,
    from_flat_path,
    parse_flat_path,
    path_kind,
    to_flat_path,
    to_lv_path,
    to_os_path,
    to_portable_path,
)


def test_non_ascii_component_bytes_raise_flat_path_error() -> None:
    data = build_flat_path(1, ["ab"]).replace(b"ab", b"a\xe9")
    with pytest.raises(FlatPathError, match="component 0 is not ASCII"):
        parse_flat_path(data)


@pytest.mark.parametrize("bad", [True, "0", 1.0, None])
def test_a_path_type_that_is_not_an_integer_is_a_type_error(bad: object) -> None:
    with pytest.raises(TypeError, match="path type must be an integer"):
        FlatPath(bad, ())  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", [-1, 0x10000])
def test_a_path_type_outside_u16_is_refused(bad: int) -> None:
    with pytest.raises(FlatPathError, match="u16"):
        FlatPath(bad, ())


def test_components_are_stored_as_a_tuple_of_str() -> None:
    flat = FlatPath(1, ["a", "b"])  # type: ignore[arg-type]
    assert flat.components == ("a", "b")
    assert flat == FlatPath(1, ("a", "b"))
    assert hash(flat) == hash(FlatPath(1, ("a", "b")))


@pytest.mark.parametrize("bad", ["ab", b"ab", 5, [1]])
def test_components_must_be_an_iterable_of_str(bad: object) -> None:
    with pytest.raises(TypeError):
        FlatPath(1, bad)  # type: ignore[arg-type]


def test_component_limits_are_checked_at_construction() -> None:
    assert len(FlatPath(1, ("x" * 255,)).to_bytes()) == 8 + 4 + 256
    with pytest.raises(FlatPathError, match="too long"):
        FlatPath(1, ("x" * 256,))
    with pytest.raises(FlatPathError, match="not ASCII"):
        FlatPath(1, ("caf\u00e9",))
    assert len(FlatPath(1, ("",) * 0xFFFF).components) == 0xFFFF
    with pytest.raises(FlatPathError, match="too many components"):
        FlatPath(1, ("",) * 0x10000)


def test_bytes_like_input_is_read_and_text_is_refused() -> None:
    golden = bytes.fromhex("505448300000000b0000000201430466696c65")
    expected = FlatPath(0, ("C", "file"))
    assert parse_flat_path(bytearray(golden)) == expected
    assert parse_flat_path(memoryview(golden)) == expected
    with pytest.raises(TypeError, match="bytes-like"):
        parse_flat_path(golden.hex())  # type: ignore[arg-type]


@pytest.mark.parametrize("part", [".", "..", "a/b"])
def test_literal_dots_and_slashes_in_components_are_refused(part: str) -> None:
    data = build_flat_path(1, ["x", part])
    for platform in ("windows", "posix"):
        with pytest.raises(FlatPathError):
            from_flat_path(data, platform=platform)


@pytest.mark.parametrize("part", ["a\\b", "a:b"])
def test_windows_special_characters_are_refused_only_on_windows(part: str) -> None:
    data = build_flat_path(1, [part])
    with pytest.raises(FlatPathError, match="separator"):
        from_flat_path(data, platform="windows")
    assert from_flat_path(data, platform="posix") == PurePosixPath(part)


def test_up_levels_map_both_ways() -> None:
    data = to_flat_path("../../a/b.vi", platform="windows")
    assert parse_flat_path(data) == FlatPath(1, ("", "", "a", "b.vi"))
    assert from_flat_path(data, platform="windows") == PureWindowsPath("../../a/b.vi")
    assert parse_flat_path(to_flat_path("C:/x/../y", platform="windows")).components == (
        "C",
        "x",
        "",
        "y",
    )


@pytest.mark.parametrize(
    ("value", "platform", "message"),
    [
        ("\\\\server\\share\\x", "windows", "UNC"),
        ("\\x", "windows", "driveless"),
        ("C:x", "windows", "drive-relative"),
        ("//x", "posix", "//"),
    ],
)
def test_unflattenable_paths_are_refused(value: str, platform: str, message: str) -> None:
    with pytest.raises(FlatPathError, match=message):
        to_flat_path(value, platform=platform)


def test_a_pure_path_keeps_its_flavor_and_only_relative_paths_cross() -> None:
    assert to_flat_path(PurePosixPath("/usr")) == to_flat_path("/usr", platform="posix")
    with pytest.raises(FlatPathError, match="anchored"):
        to_flat_path(PurePosixPath("/usr"), platform="windows")
    assert to_lv_path(PureWindowsPath("a\\b"), platform="posix") == "a/b"
    with pytest.raises(PortablePathError, match="anchored"):
        to_lv_path(PureWindowsPath("C:/x"), platform="posix")
    with pytest.raises(PortablePathError, match="colon"):
        to_lv_path(PurePosixPath("x/a:b"), platform="windows")


def test_platform_names_are_case_insensitive_and_checked() -> None:
    assert path_kind("C:\\x", platform="WINDOWS").value == "absolute"
    assert path_kind("C:\\x", platform=Platform.POSIX).value == "relative"
    with pytest.raises(ValueError, match="unknown platform"):
        to_os_path("x", platform="mac")
    with pytest.raises(TypeError, match="platform must be"):
        to_os_path("x", platform=3)  # type: ignore[arg-type]


@pytest.mark.parametrize("call", [path_kind, to_os_path])
def test_text_functions_refuse_non_strings(call: object) -> None:
    with pytest.raises(TypeError, match="must be a str"):
        call(b"C:\\x", platform="windows")  # type: ignore[operator]


def test_messages_quote_at_most_40_characters_of_a_value() -> None:
    huge = "C:" + "x" * 100_000
    with pytest.raises(PortablePathError) as raised:
        to_portable_path(huge, platform="windows")
    assert len(str(raised.value)) < 200
    assert "100002 characters" in str(raised.value)


def test_a_component_overrunning_by_one_byte_is_named_as_an_overrun() -> None:
    data = bytearray(build_flat_path(1, ["abc"]))
    data[12] = 4  # the length byte now claims one byte more than the buffer holds
    with pytest.raises(FlatPathError, match="component 0 of 4 bytes overruns the buffer"):
        parse_flat_path(bytes(data))
