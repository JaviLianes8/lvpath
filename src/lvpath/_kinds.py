"""The three LabVIEW path kinds and the not-a-path error."""

from __future__ import annotations

from enum import Enum


class PathKind(Enum):
    """Whether a LabVIEW path is absolute, relative or the not-a-path value.

    >>> from lvpath import path_kind
    >>> path_kind("../a", platform="posix") is PathKind.RELATIVE
    True
    >>> PathKind("not_a_path")
    <PathKind.NOT_A_PATH: 'not_a_path'>
    """

    __module__ = "lvpath"

    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    NOT_A_PATH = "not_a_path"


class NotAPathError(ValueError):
    """Raised when a LabVIEW not-a-path value is converted to an OS path.

    LabVIEW's ``<Not A Path>`` has no operating-system equivalent, so there is
    no ``PurePath`` to return. Check :func:`lvpath.path_kind` first to avoid it.

    >>> from lvpath import to_os_path
    >>> to_os_path("", platform="windows")
    Traceback (most recent call last):
    ...
    lvpath.NotAPathError: LabVIEW not-a-path has no OS path
    >>> issubclass(NotAPathError, ValueError)
    True
    """

    __module__ = "lvpath"
