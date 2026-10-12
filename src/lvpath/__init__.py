"""Convert between LabVIEW path strings and native OS paths.

The textual surface (:func:`to_os_path`, :func:`to_lv_path`, :func:`path_kind`)
models LabVIEW's ``Path To String`` / ``String To Path``. The flattened surface
(:class:`FlatPath`, :func:`to_flat_path`, :func:`from_flat_path` and friends)
models the binary ``Flatten To String`` ``PTH0`` form. The portable surface
(:func:`from_portable_path`, :func:`to_portable_path`) models the
platform-independent form LabVIEW writes into configuration and project files,
such as ``/C/DIR1/DIR2`` for ``C:\\DIR1\\DIR2``.
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
from ._portable import PortablePathError, from_portable_path, to_portable_path

__version__ = "0.3.0"

__all__ = [
    "SIGNATURE",
    "FlatPath",
    "FlatPathError",
    "FlatPathType",
    "NotAPathError",
    "PathKind",
    "Platform",
    "PortablePathError",
    "build_flat_path",
    "from_flat_path",
    "from_portable_path",
    "parse_flat_path",
    "path_kind",
    "to_flat_path",
    "to_lv_path",
    "to_os_path",
    "to_portable_path",
]
