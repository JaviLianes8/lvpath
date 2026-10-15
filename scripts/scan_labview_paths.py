"""Collect flattened paths that LabVIEW wrote into the files of a local install.

LabVIEW saves path constants, default values and the links between VIs inside its
own files as ``PTH0`` records. This script walks an install, finds every complete
record and writes ``tests/fixtures/labview2026_flat.json``: a summary of the whole
scan plus a small set of chosen records with the file and offset each came from.
Only the record bytes are kept; nothing else from the NI files is copied.

    python scripts/scan_labview_paths.py "C:/Program Files/National Instruments/LabVIEW 2026"
"""

from __future__ import annotations

import datetime
import json
import os
import struct
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "labview2026_flat.json"

# (file inside the install, the kind of record wanted from it, why it was chosen)
CHOSEN = [
    (
        "vi.lib/Platform/dotnet.llb/To .NET Core Object.vi",
        "drive",
        "absolute Windows path, drive C",
    ),
    ("vi.lib/MakerHub/LINX/Private/Utilties/SSH/SSH Close.vi", "usr", "absolute macOS path"),
    ("examples/Channels/Measure And Log/Measure And Log Main.vi", "empty", "absolute, no part"),
    ("resource/labview.rsc", "type2", "the only record with path type 2"),
    ("vi.lib/AppBuilder/AB_API_Simple/Build.vi", "symbolic", "symbolic <vilib> prefix"),
]
WANTED: dict[str, Callable[[int, list[bytes]], bool]] = {
    "drive": lambda t, parts: t == 0 and parts[:1] == [b"C"],
    "usr": lambda t, parts: t == 0 and parts[:1] == [b"usr"],
    "empty": lambda t, parts: t == 0 and not parts,
    "type2": lambda t, parts: t == 2,
    "symbolic": lambda t, parts: t == 0 and parts[:1] == [b"<vilib>"],
}


def records(data: bytes) -> list[tuple[int, int, list[bytes]]]:
    """Every complete PTH0 record in ``data`` as (offset, path type, components)."""
    found = []
    start = data.find(b"PTH0")
    while start != -1:
        parsed = _parse(data, start)
        if parsed is not None:
            found.append((start, *parsed))
        start = data.find(b"PTH0", start + 1)
    return found


def _parse(data: bytes, start: int) -> tuple[int, list[bytes]] | None:
    if start + 12 > len(data):
        return None
    total, path_type, count = struct.unpack_from(">IHH", data, start + 4)
    body = data[start + 8 : start + 8 + total]
    if total < 4 or len(body) != total:
        return None
    parts, offset = [], 4
    for _ in range(count):
        if offset >= len(body) or offset + 1 + body[offset] > len(body):
            return None
        parts.append(body[offset + 1 : offset + 1 + body[offset]])
        offset += 1 + body[offset]
    return (path_type, parts) if offset == len(body) else None


def resolve_link(root: Path, source: str, parts: list[bytes]) -> Path:
    """Follow a relative link from the file holding it; an empty part is one level up."""
    here = root / source
    for part in parts:
        here = here.parent if part == b"" else here / part.decode("ascii")
    return here


def main(root: Path) -> None:
    types: Counter[int] = Counter()
    up_links = up_found = 0
    chosen: list[dict[str, object]] = []
    picked_up: set[int] = set()
    for folder, _, names in os.walk(root):
        for name in sorted(names):
            path = Path(folder) / name
            if path.stat().st_size > 50_000_000:
                continue
            source = path.relative_to(root).as_posix()
            found = records(path.read_bytes())
            for index, (offset, path_type, parts) in enumerate(found):
                types[path_type] += 1
                if path_type == 1 and parts and parts[0] == b"":
                    up_links += 1
                    target = resolve_link(root, source, parts)
                    if target.exists():
                        up_found += 1
                        ups = parts.count(b"")
                        if ups not in picked_up and ups <= 6:
                            picked_up.add(ups)
                            note = f"relative link with {ups} level(s) up"
                            chosen.append(_row(source, offset, found, index, note, root, target))
            for wanted, kind, note in CHOSEN:
                if source != wanted:
                    continue
                pick = next(i for i, (_, t, parts) in enumerate(found) if WANTED[kind](t, parts))
                chosen.append(_row(source, found[pick][0], found, pick, note, root, None))
    summary = {
        "labview": "LabVIEW 2026 Community 26.3.1f1 (Windows x64), install on the author's PC",
        "scanned": datetime.date.today().isoformat(),
        "records_by_path_type": {str(k): v for k, v in sorted(types.items())},
        "relative_links_with_up_levels": up_links,
        "of_which_resolve_to_an_existing_file": up_found,
    }
    text = json.dumps({"scan": summary, "records": chosen}, indent=2) + "\n"
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps(summary, indent=2))


def _row(
    source: str,
    offset: int,
    found: list[tuple[int, int, list[bytes]]],
    index: int,
    note: str,
    root: Path,
    target: Path | None,
) -> dict[str, object]:
    path_type = found[index][1]
    data = root.joinpath(source).read_bytes()
    total = struct.unpack_from(">I", data, offset + 4)[0]
    row: dict[str, object] = {
        "source": source,
        "offset": offset,
        "note": note,
        "path_type": path_type,
        "hex": data[offset : offset + 8 + total].hex(),
    }
    if target is not None:
        row["resolves_to"] = target.relative_to(root).as_posix()
    return row


if __name__ == "__main__":
    main(Path(sys.argv[1]))
