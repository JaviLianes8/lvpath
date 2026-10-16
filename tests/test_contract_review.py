"""Contracts from the independent review's mutation sweep."""

from __future__ import annotations

from pathlib import PureWindowsPath

import pytest

import lvpath
from lvpath._text import type_name


@pytest.mark.parametrize("size", [127, 128, 200, 255])
def test_the_length_byte_holds_the_full_component_size(size: int) -> None:
    data = lvpath.build_flat_path(1, ["a" * size])
    assert data[12] == size
    assert lvpath.parse_flat_path(data).components == ("a" * size,)


def test_a_lower_case_drive_decodes_as_labview_writes_it() -> None:
    data = lvpath.build_flat_path(0, ["c", "ni-rt", "startup"])
    got = lvpath.from_flat_path(data, platform="windows")
    assert got == PureWindowsPath("c:/ni-rt/startup")
    assert str(got) == "c:\\ni-rt\\startup"


class _Lying(str):
    def __str__(self) -> str:
        return "\\\\?\\C:\\x"


def test_to_portable_path_reads_the_plain_text_of_a_str_subclass() -> None:
    assert lvpath.to_portable_path(_Lying("C:/a"), platform="windows") == "/C/a"


def test_a_non_iterable_components_value_is_named_in_the_message() -> None:
    with pytest.raises(TypeError, match="components must be an iterable of str, not int"):
        lvpath.FlatPath(0, 5)  # type: ignore[arg-type]


def test_a_unc_flattened_path_is_refused_by_name() -> None:
    data = lvpath.build_flat_path(int(lvpath.FlatPathType.UNC), ["server", "share"])
    with pytest.raises(lvpath.FlatPathError, match="UNC"):
        lvpath.from_flat_path(data, platform="windows")


def test_a_type_name_of_exactly_40_characters_is_kept_whole() -> None:
    name = "N" * 40
    assert type_name(type(name, (), {})()) == name
    assert type_name(type("M" * 41, (), {})()) == "M" * 40 + "..."
