"""Contracts from the first adversarial review: hostile strings and missing streams."""

from __future__ import annotations

import io
import pickle
import subprocess
import sys
from pathlib import Path

import pytest

from lvpath import (
    FlatPath,
    FlatPathError,
    PathKind,
    build_flat_path,
    path_kind,
    to_flat_path,
    to_lv_path,
    to_portable_path,
)
from lvpath._cli import main

_SRC = str(Path(__file__).resolve().parents[1] / "src")


class _Liar(str):
    def __eq__(self, other: object) -> bool:
        return True

    def __hash__(self) -> int:
        return 0

    def __len__(self) -> int:
        return 1


def test_a_str_subclass_cannot_lie_about_being_empty() -> None:
    value = _Liar("a/b")
    assert to_lv_path(value, platform="posix") == "a/b"
    assert to_portable_path(value, platform="posix") == "a/b"
    assert to_flat_path(value, platform="posix") == build_flat_path(1, ["a", "b"])
    assert path_kind(value, platform="posix") is PathKind.RELATIVE


def test_a_str_subclass_cannot_lie_about_its_length() -> None:
    with pytest.raises(FlatPathError, match="too long"):
        build_flat_path(0, [_Liar("x" * 300)])


def test_a_pickle_state_that_is_not_a_dict_is_a_type_error() -> None:
    forged = pickle.dumps(FlatPath(1, ("a",))).replace(b"}", b"]", 1)
    with pytest.raises((TypeError, pickle.UnpicklingError)):
        pickle.loads(forged)


def _run_child(code: str) -> subprocess.CompletedProcess[bytes]:
    command = [sys.executable, "-c", f"import sys; sys.path.insert(0, {_SRC!r}); {code}"]
    return subprocess.run(command, capture_output=True, timeout=60)


def test_a_lone_surrogate_is_written_back_as_its_byte() -> None:
    args = "['to-labview', '--platform', 'posix', 'a\\udcffb']"
    result = _run_child(f"from lvpath._cli import main; sys.exit(main({args}))")
    assert result.returncode == 0
    assert (result.stdout.rstrip(b"\r\n"), result.stderr) == (b"a\xffb", b"")


def test_missing_streams_never_raise_or_cross_over(capsys: pytest.CaptureFixture[str]) -> None:
    out, err = sys.stdout, sys.stderr
    try:
        sys.stdout = None
        assert main(["to-labview", "--platform", "windows", "C:/x"]) == 1
        captured = io.StringIO()
        sys.stdout, sys.stderr = captured, None
        assert main(["to-native", "--platform", "windows", "/home/x"]) == 1
        assert main(["nope"]) == 2
        assert captured.getvalue() == ""
    finally:
        sys.stdout, sys.stderr = out, err
