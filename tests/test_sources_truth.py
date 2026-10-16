"""The flattened-path example of NI's public flattened-data page, read from a fetched copy.

``scripts/fetch_sources.py`` downloads the page into ``tests/fixtures/sources`` (git
ignores the copy, ``MANIFEST.json`` records URL, date, size and SHA-256). These tests
skip when the copy is absent, as in a source distribution.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path

import pytest

from lvpath import FlatPath, FlatPathType, from_flat_path, parse_flat_path, to_flat_path

_FOLDER = Path(__file__).parent / "fixtures" / "sources"
_MANIFEST = json.loads((_FOLDER / "MANIFEST.json").read_text(encoding="utf-8"))
_PAGE = _FOLDER / "ni-flattened-data.json"

pytestmark = pytest.mark.skipif(not _PAGE.is_file(), reason="run scripts/fetch_sources.py")


def _text() -> str:
    raw = _PAGE.read_bytes()
    entry = _MANIFEST["files"][0]
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    page = json.loads(raw)
    body = page.get("topic_html", "") if isinstance(page, dict) else ""
    return html.unescape(re.sub(r"<[^>]+>", " ", body))


def _example_bytes() -> bytes:
    # The page writes the bytes as groups of four hex digits right after "PTH0" is named.
    match = re.search(r"is flattened to\s+((?:[0-9A-F]{2,4}\s+){5,}[0-9A-F]{2,4})", _text())
    assert match is not None
    return bytes.fromhex("".join(match.group(1).split()))


def test_the_manifest_names_the_page_it_was_fetched_from() -> None:
    entry = _MANIFEST["files"][0]
    assert entry["url"].endswith("/flattened-data.html")
    assert entry["size"] == _PAGE.stat().st_size


def test_the_page_example_parses_to_drive_c_and_one_name() -> None:
    data = _example_bytes()
    assert data[:4] == b"PTH0"
    flat = parse_flat_path(data)
    assert flat == FlatPath(int(FlatPathType.ABSOLUTE), ("C", "file"))
    assert flat.to_bytes() == data


def test_the_page_example_bridges_to_c_file_and_back() -> None:
    data = _example_bytes()
    assert str(from_flat_path(data, platform="windows")) == "C:\\file"
    assert to_flat_path("C:\\file", platform="windows") == data
