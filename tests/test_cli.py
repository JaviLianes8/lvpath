"""In-process tests of the command line entry point."""

from __future__ import annotations

import pytest

from lvpath._cli import main

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


def test_decode_and_encode_still_work(capsys: pytest.CaptureFixture[str]) -> None:
    assert _out(capsys, "decode", "--platform", "windows", GOLDEN_HEX) == (0, "C:\\file\n", "")
    assert _out(capsys, "encode", "--platform", "windows", "C:\\file") == (0, GOLDEN_HEX + "\n", "")


def test_decode_reports_bad_hex(capsys: pytest.CaptureFixture[str]) -> None:
    status, _, err = _out(capsys, "decode", "zz")
    assert status == 1
    assert "not valid hex" in err


def test_a_missing_command_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        main([])
    assert raised.value.code == 2
    assert "usage: lvpath" in capsys.readouterr().err
