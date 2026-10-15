"""Fetch the public reference the source test reads, and record it in MANIFEST.json.

The copy stays on the maintainer's machine (git ignores it); only the manifest with the
URL, date, size and SHA-256 is tracked. Run from the repository root:

    python scripts/fetch_sources.py
"""

from __future__ import annotations

import datetime
import hashlib
import json
import urllib.request
from pathlib import Path

SOURCES = {
    "ni-flattened-data.json": "https://docs-be.ni.com/api/bundle/labview/page/flattened-data.html",
}
LICENCES = {
    "ni-flattened-data.json": "NI documentation, copyright NI; local copy only",
}

FOLDER = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "sources"


def main() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    entries = []
    for name, url in SOURCES.items():
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json, text/plain"}
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read()
        (FOLDER / name).write_bytes(body)
        entries.append(
            {
                "file": name,
                "url": url,
                "fetched": today,
                "size": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "licence": LICENCES[name],
            }
        )
    manifest = {"note": "public reference fetched for the source test", "files": entries}
    text = json.dumps(manifest, indent=2) + "\n"
    (FOLDER / "MANIFEST.json").write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
