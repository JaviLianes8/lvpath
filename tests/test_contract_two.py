"""Contracts from the first API review: platform first, path objects, buffers, public names."""

from __future__ import annotations

import array
import mmap
import pickle
from collections.abc import Callable
from pathlib import PurePosixPath, PureWindowsPath

import pytest

import lvpath
from lvpath import (
    FlatPath,
    FlatPathError,
    FlatPathType,
    PathKind,
    PortablePathError,
    build_flat_path,
    from_portable_path,
    parse_flat_path,
    path_kind,
    to_flat_path,
    to_lv_path,
    to_os_path,
    to_portable_path,
)

_EMPTY_CALLS: list[Callable[[object], object]] = [
    lambda p: path_kind("", platform=p),  # type: ignore[arg-type]
    lambda p: to_os_path("", platform=p),  # type: ignore[arg-type]
    lambda p: to_lv_path("", platform=p),  # type: ignore[arg-type]
    lambda p: to_lv_path(None, platform=p),  # type: ignore[arg-type]
    lambda p: to_portable_path("", platform=p),  # type: ignore[arg-type]
    lambda p: from_portable_path("", platform=p),  # type: ignore[arg-type]
]


@pytest.mark.parametrize("call", _EMPTY_CALLS)
def test_the_platform_is_checked_first_even_for_an_empty_path(
    call: Callable[[object], object],
) -> None:
    with pytest.raises(ValueError, match="unknown platform"):
        call("bogus")
    with pytest.raises(TypeError, match="platform must be"):
        call(3)


def test_path_objects_are_still_read_as_text() -> None:
    assert to_os_path(PureWindowsPath("C:/x"), platform="windows") == PureWindowsPath("C:/x")  # type: ignore[arg-type]
    assert path_kind(PurePosixPath("/x"), platform="posix") is PathKind.ABSOLUTE  # type: ignore[arg-type]
    assert from_portable_path(PurePosixPath("/x"), platform="posix") == PurePosixPath("/x")  # type: ignore[arg-type]


def test_a_backslash_component_may_not_cross_to_windows() -> None:
    with pytest.raises(PortablePathError, match="backslash"):
        to_lv_path(PurePosixPath("a\\b"), platform="windows")
    with pytest.raises(FlatPathError, match="backslash"):
        to_flat_path(PurePosixPath("a\\b"), platform="windows")


def test_any_buffer_is_read_and_text_is_refused() -> None:
    golden = bytes.fromhex("505448300000000b0000000201430466696c65")
    expected = FlatPath(0, ("C", "file"))
    assert parse_flat_path(array.array("B", golden)) == expected  # type: ignore[arg-type]
    with mmap.mmap(-1, len(golden)) as mapped:
        mapped.write(golden)
        assert parse_flat_path(mapped) == expected  # type: ignore[arg-type]
    for bad in (golden.hex(), 5, None):
        with pytest.raises(TypeError, match="bytes-like"):
            parse_flat_path(bad)  # type: ignore[arg-type]


def test_build_flat_path_refuses_a_string_of_components() -> None:
    with pytest.raises(TypeError, match="iterable of str"):
        build_flat_path(1, "ab")


def test_the_path_type_is_stored_as_a_plain_int() -> None:
    flat = FlatPath(FlatPathType.RELATIVE, ())
    assert type(flat.path_type) is int
    assert repr(flat) == "FlatPath(path_type=1, components=())"


def test_out_of_range_types_are_shown_as_numbers_or_by_size() -> None:
    with pytest.raises(FlatPathError, match=r"u16 range: 70000$"):
        FlatPath(70000, ())
    with pytest.raises(FlatPathError, match="an integer of 16610 bits"):
        FlatPath(10**5000, ())


@pytest.mark.parametrize(
    "name", ["FlatPath", "FlatPathType", "PathKind", "Platform", "FlatPathError"]
)
def test_public_classes_report_the_package_as_their_module(name: str) -> None:
    assert getattr(lvpath, name).__module__ == "lvpath"


def test_values_pickle_under_the_public_module() -> None:
    for value in (FlatPath(1, ("a",)), PathKind.RELATIVE, lvpath.Platform.POSIX):
        data = pickle.dumps(value)
        assert b"lvpath._" not in data
        assert pickle.loads(data) == value
