from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath

import pytest

from lvpath import NotAPathError, PathKind, path_kind, to_lv_path, to_os_path


def test_absolute_windows_path_round_trips() -> None:
    lv = "C:\\Users\\test\\file.txt"
    os_path = to_os_path(lv, platform="windows")
    assert os_path == PureWindowsPath("C:/Users/test/file.txt")
    assert to_lv_path(os_path, platform="windows") == lv


def test_absolute_posix_path_round_trips() -> None:
    lv = "/usr/local/bin"
    os_path = to_os_path(lv, platform="posix")
    assert os_path == PurePosixPath("/usr/local/bin")
    assert to_lv_path(os_path, platform="posix") == lv


def test_relative_path_round_trips() -> None:
    lv = "data\\logs\\run.txt"
    os_path = to_os_path(lv, platform="windows")
    assert to_lv_path(os_path, platform="windows") == lv


def test_empty_string_is_not_a_path() -> None:
    assert path_kind("", platform="windows") is PathKind.NOT_A_PATH
    assert path_kind("", platform="posix") is PathKind.NOT_A_PATH


def test_not_a_path_has_no_os_path() -> None:
    with pytest.raises(NotAPathError):
        to_os_path("", platform="posix")


def test_none_serializes_to_not_a_path() -> None:
    assert to_lv_path(None, platform="windows") == ""
    assert to_lv_path("", platform="posix") == ""


def test_forward_slashes_parse_as_a_windows_path() -> None:
    os_path = to_os_path("C:/data/run.txt", platform="windows")
    assert to_lv_path(os_path, platform="windows") == "C:\\data\\run.txt"


def test_serialize_normalises_separators_to_the_target() -> None:
    assert to_lv_path("a/b/c", platform="windows") == "a\\b\\c"
    assert to_lv_path("a/b/c", platform="posix") == "a/b/c"


def test_relative_path_converts_across_platforms() -> None:
    windows = to_os_path("reports\\q1\\data.txt", platform="windows")
    assert to_lv_path(windows, platform="posix") == "reports/q1/data.txt"


def test_kind_detects_absolute_relative_and_unc() -> None:
    assert path_kind("C:\\x", platform="windows") is PathKind.ABSOLUTE
    assert path_kind("\\\\server\\share\\x", platform="windows") is PathKind.ABSOLUTE
    assert path_kind("sub\\file", platform="windows") is PathKind.RELATIVE
    assert path_kind("/etc/hosts", platform="posix") is PathKind.ABSOLUTE
    assert path_kind("etc/hosts", platform="posix") is PathKind.RELATIVE


def test_unknown_platform_is_rejected() -> None:
    with pytest.raises(ValueError):
        to_os_path("/x", platform="vxworks")
