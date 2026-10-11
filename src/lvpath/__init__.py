"""Convert between LabVIEW path strings and native OS paths.

The textual surface (:func:`to_os_path`, :func:`to_lv_path`, :func:`path_kind`)
models LabVIEW's ``Path To String`` / ``String To Path``. The flattened surface
(:class:`FlatPath`, :func:`to_flat_path`, :func:`from_flat_path` and friends)
models the binary ``Flatten To String`` ``PTH0`` form.
"""

from __future__ import annotations

from ._convert import path_kind, to_lv_path, to_os_path
from ._flatbridge import from_flat_path, to_flat_path
from ._flatten import (
    SIGNATURE,
    FlatPath,
    FlatPathError,
    FlatPathType,
    build_flat_path,
    parse_flat_path,
)
from ._kinds import NotAPathError, PathKind
from ._platform import Platform

__version__ = "0.2.0"

__all__ = [
    "SIGNATURE",
    "FlatPath",
    "FlatPathError",
    "FlatPathType",
    "NotAPathError",
    "PathKind",
    "Platform",
    "build_flat_path",
    "from_flat_path",
    "parse_flat_path",
    "path_kind",
    "to_flat_path",
    "to_lv_path",
    "to_os_path",
]
