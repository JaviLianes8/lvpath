"""Flattened paths LabVIEW 2026 wrote into its own installed files.

``tests/fixtures/labview2026_flat.json`` was produced by
``scripts/scan_labview_paths.py`` on the author's LabVIEW 2026 install: it keeps a
summary of every ``PTH0`` record found and eleven chosen records, each with the file
and byte offset it came from. The relative links show LabVIEW's up-level rule: an
empty component is ``..``, applied to the file that holds the link.

Set ``LVPATH_LABVIEW_ROOT`` to an install folder to run the full sweep as well.
"""

from __future__ import annotations

import json
import os
import posixpath
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

import pytest

from lvpath import FlatPathError, from_flat_path, parse_flat_path, to_flat_path

_FIXTURE = Path(__file__).parent / "fixtures" / "labview2026_flat.json"
_DATA = json.loads(_FIXTURE.read_text(encoding="utf-8"))
_RECORDS = _DATA["records"]
_LINKS = [row for row in _RECORDS if "resolves_to" in row]


def _by_note(start: str) -> bytes:
    return bytes.fromhex(next(r["hex"] for r in _RECORDS if r["note"].startswith(start)))


@pytest.mark.parametrize("row", _RECORDS, ids=lambda row: row["note"])
def test_every_record_round_trips_byte_for_byte(row: dict[str, Any]) -> None:
    data = bytes.fromhex(row["hex"])
    flat = parse_flat_path(data)
    assert flat.path_type == row["path_type"]
    assert flat.to_bytes() == data


def test_the_scan_found_the_three_path_types_and_links_that_resolve() -> None:
    scan = _DATA["scan"]
    assert set(scan["records_by_path_type"]) == {"0", "1", "2"}
    assert scan["records_by_path_type"]["2"] == 1
    assert (
        scan["of_which_resolve_to_an_existing_file"] > 0.9 * scan["relative_links_with_up_levels"]
    )
    assert len(_LINKS) == 6


@pytest.mark.parametrize("row", _LINKS, ids=lambda row: row["note"])
def test_an_empty_component_is_one_level_up_from_the_holding_file(row: dict[str, Any]) -> None:
    data = bytes.fromhex(row["hex"])
    link = from_flat_path(data, platform="posix")
    assert link.parts[0] == ".."
    assert posixpath.normpath(f"{row['source']}/{link}") == row["resolves_to"]
    assert to_flat_path(link, platform="posix") == data
    windows = from_flat_path(data, platform="windows")
    assert windows == PureWindowsPath(*link.parts)
    assert to_flat_path(windows, platform="windows") == data


def test_a_drive_path_decodes_on_both_flavors_and_encodes_back() -> None:
    data = _by_note("absolute Windows path")
    windows = from_flat_path(data, platform="windows")
    assert windows.drive == "C:"
    assert windows.parts[1:3] == ("Program Files", "dotnet")
    assert to_flat_path(windows, platform="windows") == data
    posix = from_flat_path(data, platform="posix")
    assert posix.parts[:3] == ("/", "C", "Program Files")
    assert to_flat_path(posix, platform="posix") == data


def test_a_macos_path_decodes_on_posix_and_is_refused_on_windows() -> None:
    data = _by_note("absolute macOS path")
    assert from_flat_path(data, platform="posix") == PurePosixPath(
        "/usr/lib/system/libsystem_c.dylib"
    )
    assert to_flat_path("/usr/lib/system/libsystem_c.dylib", platform="posix") == data
    with pytest.raises(FlatPathError, match="not a Windows drive letter"):
        from_flat_path(data, platform="windows")


def test_the_absolute_path_with_no_component_is_the_posix_root() -> None:
    data = _by_note("absolute, no part")
    assert data == bytes.fromhex("505448300000000400000000")
    assert from_flat_path(data, platform="posix") == PurePosixPath("/")
    assert to_flat_path("/", platform="posix") == data
    with pytest.raises(FlatPathError, match="no component"):
        from_flat_path(data, platform="windows")


def test_path_type_two_is_kept_but_not_interpreted() -> None:
    data = _by_note("the only record with path type 2")
    assert parse_flat_path(data).components == ()
    for platform in ("windows", "posix"):
        with pytest.raises(FlatPathError, match="path type 2"):
            from_flat_path(data, platform=platform)


def test_a_symbolic_prefix_is_refused_on_both_flavors() -> None:
    data = _by_note("symbolic")
    assert parse_flat_path(data).components[0] == "<vilib>"
    for platform in ("windows", "posix"):
        with pytest.raises(FlatPathError, match="symbolic"):
            from_flat_path(data, platform=platform)


_ROOT = os.environ.get("LVPATH_LABVIEW_ROOT")


@pytest.mark.skipif(not _ROOT, reason="set LVPATH_LABVIEW_ROOT to sweep a LabVIEW install")
def test_full_sweep_of_an_install() -> None:  # pragma: no cover - opt-in
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "scan", Path(__file__).parent.parent / "scripts" / "scan_labview_paths.py"
    )
    assert spec is not None and spec.loader is not None
    scan = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scan)
    root = Path(str(_ROOT))
    checked = 0
    for folder, _, names in os.walk(root):
        for name in names:
            path = Path(folder) / name
            if path.stat().st_size > 50_000_000:
                continue
            data = path.read_bytes()
            for offset, path_type, _parts in scan.records(data):
                total = int.from_bytes(data[offset + 4 : offset + 8], "big")
                raw = data[offset : offset + 8 + total]
                assert parse_flat_path(raw).to_bytes() == raw
                if path_type == 1:
                    link = from_flat_path(raw, platform="posix")
                    assert to_flat_path(link, platform="posix") == raw
                checked += 1
    assert checked > 300_000
