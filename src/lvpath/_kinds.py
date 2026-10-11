"""The three LabVIEW path kinds and the not-a-path error."""

from __future__ import annotations

from enum import Enum


class PathKind(Enum):
    """Whether a LabVIEW path is absolute, relative or the not-a-path value."""

    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    NOT_A_PATH = "not_a_path"


class NotAPathError(ValueError):
    """Raised when a LabVIEW not-a-path value is converted to an OS path.

    LabVIEW's ``<Not A Path>`` has no operating-system equivalent, so there is
    no ``PurePath`` to return. Check :func:`lvpath.path_kind` first to avoid it.
    """
