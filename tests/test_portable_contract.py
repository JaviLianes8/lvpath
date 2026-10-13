"""Contract: the complete portable-path promise against real LabVIEW 2026 files.

``fixtures/labview2026_paths.json`` holds path values found in files shipped with
LabVIEW 2026, each with the source file and setting it was seen in. Every value must convert in
both directions on both platform flavors and round-trip exactly. The NI forum
example and the NI ``PTH0`` golden vector tie the portable string, the native
path and the flattened bytes together.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from lvpath import (
    NotAPathError,
    PortablePathError,
    from_flat_path,
    from_portable_path,
    to_flat_path,
    to_portable_path,
)

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "labview2026_paths.json").read_text(encoding="utf-8")
)
PORTABLE: list[dict[str, Any]] = FIXTURE["portable_form"]
NATIVE: list[dict[str, Any]] = FIXTURE["native_form"]
GOLDEN = bytes.fromhex("505448300000000b0000000201430466696c65")


def _ids(rows: list[dict[str, Any]]) -> list[str]:
    return [f"{Path(row['source']).name}:{row['portable'] or '<empty>'}" for row in rows]


def test_the_fixture_covers_every_form() -> None:
    values = [row["portable"] for row in PORTABLE]
    assert any(re.match(r"^/[A-Z]/", v) for v in values), "upper-case drive"
    assert any(re.match(r"^/[a-z]/", v) for v in values), "lower-case drive"
    assert any(v.startswith("../") for v in values), "up-level relative"
    assert any(v and not v.startswith(("/", ".")) for v in values), "plain relative"
    assert any(" " in v for v in values), "spaces"
    assert any(v.startswith("/home/") for v in values), "POSIX absolute"
    assert "" in values, "empty <Not A Path>"
    assert len(NATIVE) >= 1, "native Windows form"


def test_every_row_records_its_provenance_and_no_source_line() -> None:
    for row in PORTABLE + NATIVE:
        assert row["source"].startswith("C:/Program Files/National Instruments/LabVIEW 2026/")
        assert row["key"]
        assert "raw" not in row


@pytest.mark.parametrize("row", PORTABLE, ids=_ids(PORTABLE))
def test_portable_value_reads_as_windows(row: dict[str, Any]) -> None:
    if row["portable"] == "":
        with pytest.raises(NotAPathError):
            from_portable_path(row["portable"], platform="windows")
    elif row["windows"] is None:
        with pytest.raises(PortablePathError):
            from_portable_path(row["portable"], platform="windows")
    else:
        assert str(from_portable_path(row["portable"], platform="windows")) == row["windows"]


@pytest.mark.parametrize("row", PORTABLE, ids=_ids(PORTABLE))
def test_portable_value_reads_as_posix(row: dict[str, Any]) -> None:
    if row["portable"] == "":
        with pytest.raises(NotAPathError):
            from_portable_path(row["portable"], platform="posix")
    else:
        assert str(from_portable_path(row["portable"], platform="posix")) == row["posix"]


@pytest.mark.parametrize("row", PORTABLE, ids=_ids(PORTABLE))
def test_native_value_writes_back_the_exact_portable_string(row: dict[str, Any]) -> None:
    if row["windows"] is not None:
        assert to_portable_path(row["windows"], platform="windows") == row["portable"]
    if row["posix"] is not None:
        assert to_portable_path(row["posix"], platform="posix") == row["portable"]
    if row["portable"] == "":
        assert to_portable_path(None, platform="windows") == ""


@pytest.mark.parametrize("row", PORTABLE, ids=_ids(PORTABLE))
def test_portable_value_round_trips_through_native(row: dict[str, Any]) -> None:
    for platform in ("windows", "posix"):
        if row[platform] is None:
            continue
        native = from_portable_path(row["portable"], platform=platform)
        assert to_portable_path(native) == row["portable"]
        assert to_portable_path(str(native), platform=platform) == row["portable"]


@pytest.mark.parametrize("row", NATIVE, ids=_ids(NATIVE))
def test_native_form_value_converts_and_round_trips(row: dict[str, Any]) -> None:
    assert to_portable_path(row["windows"], platform="windows") == row["portable"]
    assert str(from_portable_path(row["portable"], platform="windows")) == row["windows"]
    assert str(from_portable_path(row["windows"], platform="windows")) == row["windows"]


# No shipped LabVIEW 2026 file holds a bare drive or a UNC value, so these parts of
# the promise are pinned by synthetic rows that follow the same convention.
SYNTHETIC = [
    ("/D", "D:\\"),
    ("/e/data", "e:\\data"),
    ("//server/share", "\\\\server\\share\\"),
    ("//server/share/dir/f.ini", "\\\\server\\share\\dir\\f.ini"),
    ("//srv/c$/x", "\\\\srv\\c$\\x"),
]


@pytest.mark.parametrize(("portable", "windows"), SYNTHETIC)
def test_bare_drive_and_unc_values_convert_and_round_trip(portable: str, windows: str) -> None:
    native = from_portable_path(portable, platform="windows")
    assert str(native) == windows
    assert to_portable_path(native) == portable
    assert to_portable_path(windows, platform="windows") == portable
    assert str(from_portable_path(portable, platform="posix")) == portable


def test_ni_forum_example_converts_both_ways() -> None:
    # NI forum "Config files and the PATH": C:\DIR1\DIR2 is saved as /C/DIR1/DIR2.
    assert str(from_portable_path("/C/DIR1/DIR2", platform="windows")) == "C:\\DIR1\\DIR2"
    assert to_portable_path("C:\\DIR1\\DIR2", platform="windows") == "/C/DIR1/DIR2"


def test_portable_string_native_path_and_ni_golden_vector_agree() -> None:
    # NI documents C:\File flattening to GOLDEN; the bytes spell the name "file".
    native = from_portable_path("/C/file", platform="windows")
    assert to_flat_path(native, platform="windows") == GOLDEN
    assert to_portable_path(from_flat_path(GOLDEN, platform="windows")) == "/C/file"
