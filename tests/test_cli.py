"""In-process tests of the command line entry point."""

from __future__ import annotations

import shlex

import pytest

from lvpath._cli import _EXAMPLES, main

GOLDEN_HEX = "505448300000000b0000000201430466696c65"


def _out(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    status = main(list(argv))
    captured = capsys.readouterr()
    return status, captured.out, captured.err


def test_to_native_converts_a_drive_path(capsys: pytest.CaptureFixture[str]) -> None:
    status, out, err = _out(capsys, "to-native", "--platform", "windows", "/C/DIR1/DIR2")
    assert (status, out, err) == (0, "C:\\DIR1\\DIR2\n", "")


def test_to_labview_converts_a_unc_path(capsys: pytest.CaptureFixture[str]) -> None:
    status, out, _ = _out(capsys, "to-labview", "--platform", "windows", "\\\\srv\\share\\a")
    assert (status, out) == (0, "//srv/share/a\n")


def test_to_labview_prints_not_a_path_as_an_empty_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert _out(capsys, "to-labview", "--platform", "posix", "") == (0, "\n", "")


def test_to_native_errors_go_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    status, out, err = _out(capsys, "to-native", "--platform", "windows", "C:file")
    assert status == 1
    assert out == ""
    assert err.startswith("lvpath: ") and "drive-relative" in err


def test_to_labview_errors_go_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    status, out, err = _out(capsys, "to-labview", "--platform", "windows", "\\rooted")
    assert (status, out) == (1, "")
    assert "rooted without a drive" in err


def test_non_ascii_paths_print_in_both_directions(capsys: pytest.CaptureFixture[str]) -> None:
    name = "Data \u0101\u4e2d"
    status, out, err = _out(capsys, "to-native", "--platform", "windows", f"/C/{name}")
    assert (status, out, err) == (0, f"C:\\{name}\n", "")
    status, out, err = _out(capsys, "to-labview", "--platform", "windows", f"C:\\{name}")
    assert (status, out, err) == (0, f"/C/{name}\n", "")


def test_a_malformed_drive_is_reported(capsys: pytest.CaptureFixture[str]) -> None:
    status, out, err = _out(capsys, "to-native", "--platform", "windows", "/C:/x")
    assert (status, out) == (1, "")
    assert "malformed drive" in err


def test_decode_and_encode_still_work(capsys: pytest.CaptureFixture[str]) -> None:
    assert _out(capsys, "decode", "--platform", "windows", GOLDEN_HEX) == (0, "C:\\file\n", "")
    assert _out(capsys, "encode", "--platform", "windows", "C:\\file") == (0, GOLDEN_HEX + "\n", "")


def test_decode_reports_bad_hex(capsys: pytest.CaptureFixture[str]) -> None:
    status, _, err = _out(capsys, "decode", "zz")
    assert status == 1
    assert "not valid hex" in err


def test_a_missing_command_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 2
    assert "usage: lvpath" in capsys.readouterr().err


def test_every_help_example_runs_and_prints_what_it_states(
    capsys: pytest.CaptureFixture[str],
) -> None:
    lines = [line.strip() for line in _EXAMPLES.splitlines()]
    commands = [index for index, line in enumerate(lines) if line.startswith("lvpath ")]
    assert len(commands) >= 6
    for index in commands:
        status, out, err = _out(capsys, *shlex.split(lines[index])[1:])
        assert (status, err) == (0, ""), lines[index]
        following = lines[index + 1] if index + 1 < len(lines) else ""
        if following.startswith("# prints "):
            assert out == following.removeprefix("# prints ") + "\n", lines[index]


def test_hex_may_hold_spaces_anywhere(capsys: pytest.CaptureFixture[str]) -> None:
    spaced = "505 44830 0000000b00 000002014304 66696c65"
    assert _out(capsys, "decode", "--platform", "windows", spaced) == (0, "C:\\file\n", "")


def test_every_error_line_is_at_most_200_characters(capsys: pytest.CaptureFixture[str]) -> None:
    for args in (["nope" * 5000], ["decode", "--platform", "mac" * 5000, "00"]):
        assert main(args) == 2
        err = capsys.readouterr().err
        assert err.splitlines() and all(len(line) <= 200 for line in err.splitlines())
