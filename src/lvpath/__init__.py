"""Convert between LabVIEW path strings and native OS paths."""

from __future__ import annotations

from ._convert import path_kind, to_lv_path, to_os_path
from ._kinds import NotAPathError, PathKind
from ._platform import Platform

__version__ = "0.1.0"

__all__ = [
    "NotAPathError",
    "PathKind",
    "Platform",
    "path_kind",
    "to_lv_path",
    "to_os_path",
]
