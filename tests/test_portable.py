"""Unit tests for LabVIEW's portable path string form."""

from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath

import pytest

from lvpath import (
    NotAPathError,
    Platform,
    PortablePathError,
    from_portable_path,
    to_portable_path,
)


@pytest.mark.parametrize(
    ("portable", "native"),
    [
        ("/C/DIR1/DIR2", "C:\\DIR1\\DIR2"),
        ("/D", "D:\\"),
        ("/c/ni-rt/startup", "c:\\ni-rt\\startup"),
        ("//server/share/dir/f.txt", "\\\\server\\share\\dir\\f.txt"),
        ("../up/file.vi", "..\\up\\file.vi"),
        ("sub dir/My File.vi", "sub dir\\My File.vi"),
        (".", "."),
    ],
)
def test_portable_string_reads_as_a_windows_path(portable: str, native: str) -> None:
    result = from_portable_path(portable, platform="windows")
    assert isinstance(result, PureWindowsPath)
    assert str(result) == native


def test_bare_unc_share_reads_as_its_root() -> None:
    assert from_portable_path("//server/share", platform="windows") == PureWindowsPath(
        "\\\\server\\share\\"
    )


def test_native_windows_text_is_accepted_as_is() -> None:
    assert str(from_portable_path("C:\\NI Installers", platform="windows")) == "C:\\NI Installers"
    assert str(from_portable_path("\\\\srv\\sh\\a", platform="windows")) == "\\\\srv\\sh\\a"


def test_posix_reads_the_portable_form_directly() -> None:
    result = from_portable_path("/home/lvuser/natinst/bin", platform="posix")
    assert result == PurePosixPath("/home/lvuser/natinst/bin")


def test_platform_enum_is_accepted() -> None:
    assert str(from_portable_path("/E/x", platform=Platform.WINDOWS)) == "E:\\x"


def test_not_a_path_has_no_native_path() -> None:
    with pytest.raises(NotAPathError):
        from_portable_path("", platform="windows")
    with pytest.raises(NotAPathError):
        from_portable_path("", platform="posix")


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("/home/lvuser", "POSIX absolute"),
        ("//server", "UNC"),
        ("//server/", "UNC"),
        ("///share", "UNC"),
        ("C:file", "drive-relative"),
        ("\\rooted", "rooted without a drive"),
        ("\\\\?\\C:\\x", "device"),
    ],
)
def test_values_with_no_windows_equivalent_are_refused(text: str, reason: str) -> None:
    with pytest.raises(PortablePathError, match=reason):
        from_portable_path(text, platform="windows")


@pytest.mark.parametrize(
    ("native", "portable"),
    [
        ("C:\\DIR1\\DIR2", "/C/DIR1/DIR2"),
        ("C:/DIR1/DIR2", "/C/DIR1/DIR2"),
        ("D:\\", "/D"),
        ("c:\\ni-rt\\startup", "/c/ni-rt/startup"),
        ("\\\\server\\share\\dir", "//server/share/dir"),
        ("\\\\server\\share", "//server/share"),
        ("..\\up\\file.vi", "../up/file.vi"),
        ("data\\run.ini", "data/run.ini"),
        (".", "."),
    ],
)
def test_windows_path_writes_the_portable_string(native: str, portable: str) -> None:
    assert to_portable_path(native, platform="windows") == portable
    assert to_portable_path(PureWindowsPath(native)) == portable


def test_posix_path_is_already_portable() -> None:
    assert to_portable_path("/usr/local/lib", platform="posix") == "/usr/local/lib"
    assert to_portable_path(PurePosixPath("a/b")) == "a/b"


def test_none_and_empty_write_not_a_path() -> None:
    assert to_portable_path(None, platform="windows") == ""
    assert to_portable_path("", platform="posix") == ""


@pytest.mark.parametrize("native", ["C:file", "\\rooted", "\\\\?\\C:\\x", "C:"])
def test_windows_paths_with_no_portable_form_are_refused(native: str) -> None:
    with pytest.raises(PortablePathError):
        to_portable_path(native, platform="windows")


def test_a_pure_path_keeps_its_own_flavor() -> None:
    assert to_portable_path(PureWindowsPath("C:/x")) == "/C/x"
    assert to_portable_path(PurePosixPath("/C/x")) == "/C/x"


def test_relative_pure_path_crosses_flavors() -> None:
    assert to_portable_path(PurePosixPath("a/b"), platform="windows") == "a/b"
    assert to_portable_path(PureWindowsPath("a\\b"), platform="posix") == "a/b"


def test_absolute_pure_path_does_not_cross_flavors() -> None:
    with pytest.raises(PortablePathError, match="cannot carry"):
        to_portable_path(PureWindowsPath("C:/x"), platform="posix")
    with pytest.raises(PortablePathError, match="cannot carry"):
        to_portable_path(PurePosixPath("/usr"), platform="windows")


def test_unknown_platform_is_an_error() -> None:
    with pytest.raises(ValueError, match="unknown platform"):
        from_portable_path("/C/x", platform="vxworks")


# The same vectors the sibling lvconfig library pins for its stored path form, so
# both libraries agree on every value either one supports.
@pytest.mark.parametrize(
    ("native", "portable"),
    [
        ("C:\\Temp\\log.txt", "/C/Temp/log.txt"),
        ("D:\\", "/D"),
        ("\\\\server\\share\\f", "//server/share/f"),
        ("data\\run.ini", "data/run.ini"),
        ("E:\\", "/E"),
        ("a\\b\\c", "a/b/c"),
    ],
)
def test_agrees_with_the_lvconfig_stored_path_vectors(native: str, portable: str) -> None:
    assert to_portable_path(native, platform="windows") == portable
    assert str(from_portable_path(portable, platform="windows")) == native


def test_rooted_driveless_windows_path_does_not_cross_to_posix() -> None:
    with pytest.raises(PortablePathError, match="cannot carry"):
        to_portable_path(PureWindowsPath("/x"), platform="posix")


def test_posix_name_with_a_backslash_does_not_cross_to_windows() -> None:
    with pytest.raises(PortablePathError, match="backslash"):
        to_portable_path(PurePosixPath("a\\b"), platform="windows")


def test_a_trailing_newline_is_never_dropped() -> None:
    with pytest.raises(PortablePathError):
        from_portable_path("/C\n", platform="windows")
    assert from_portable_path("/C/a\n", platform="windows").name == "a\n"


def test_mixed_separators_in_a_unc_value_are_accepted() -> None:
    result = from_portable_path("//server\\share\\dir", platform="windows")
    assert str(result) == "\\\\server\\share\\dir"


@pytest.mark.parametrize("text", ["\\\\server", "//server//share", "/\\x"])
def test_incomplete_unc_values_name_the_input(text: str) -> None:
    with pytest.raises(PortablePathError, match="UNC") as raised:
        to_portable_path(text, platform="windows")
    assert repr(text) in str(raised.value)
