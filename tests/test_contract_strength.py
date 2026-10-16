"""Contracts from the blind mutation round: limits, defaults and prefixes no test pinned."""

from __future__ import annotations

import os
from pathlib import PurePosixPath, PureWindowsPath

import pytest

import lvpath
from lvpath._cli import main


def test_path_type_0xffff_is_a_valid_u16() -> None:
    data = lvpath.build_flat_path(0xFFFF, ["a"])
    assert data.hex() == "5054483000000006ffff00010161"
    flat = lvpath.parse_flat_path(data)
    assert flat.path_type == 0xFFFF
    assert flat.to_bytes() == data
    with pytest.raises(lvpath.FlatPathError):
        lvpath.FlatPath(0x10000, ())


def test_a_value_of_exactly_40_characters_is_quoted_whole() -> None:
    value = "/" + "x" * 39
    with pytest.raises(lvpath.PortablePathError) as info:
        lvpath.from_portable_path(value, platform="windows")
    assert repr(value) in str(info.value)
    assert "first 40" not in str(info.value)


def test_platform_none_follows_the_running_system() -> None:
    assert lvpath.to_lv_path("a/b") == ("a\\b" if os.name == "nt" else "a/b")
    flavor = PureWindowsPath if os.name == "nt" else PurePosixPath
    assert type(lvpath.to_os_path("a")) is flavor


@pytest.mark.parametrize("text", [" ", "  ", "\t"])
def test_only_the_empty_string_is_not_a_path(text: str) -> None:
    assert lvpath.path_kind(text, platform="posix") is lvpath.PathKind.RELATIVE
    assert lvpath.to_os_path(text, platform="posix") == PurePosixPath(text)


def test_a_mixed_slash_unc_prefix_reads_as_unc() -> None:
    got = lvpath.from_portable_path("/\\server\\share\\dir", platform="windows")
    assert got == PureWindowsPath("//server/share/dir")


@pytest.mark.parametrize("text", ["\\\\.\\C:\\x", "//./C:/x", "\\\\?\\C:\\x"])
def test_device_paths_have_no_portable_form(text: str) -> None:
    with pytest.raises(lvpath.PortablePathError, match="device path"):
        lvpath.to_portable_path(text, platform="windows")
    with pytest.raises(lvpath.PortablePathError, match="device path"):
        lvpath.from_portable_path(text, platform="windows")


def test_a_usage_error_line_stays_within_200_characters(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # 500 characters: between the 200 cap and any looser cap a mutant might use.
    assert main(["to-native", "--platform", "x" * 500, "a"]) == 2
    err = capsys.readouterr().err.splitlines()
    assert err and all(len(line) <= 200 for line in err)
