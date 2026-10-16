"""Turn a caller's ``str`` or ``PurePath`` into a pure path of the right flavor."""

from __future__ import annotations

from pathlib import PurePath, PureWindowsPath

from ._platform import Platform, flavor, resolve
from ._text import quote, type_name


def as_pure(os_path: object, platform: Platform | str | None, error: type[ValueError]) -> PurePath:
    """Parse a ``str`` with the flavor of ``platform``; keep a ``PurePath``'s own flavor.

    A ``PurePath`` is carried to the other flavor only when ``platform`` names it
    and the path is relative with no backslash inside a component; anything else
    raises ``error``, because its meaning would change on the way.

    >>> from pathlib import PurePosixPath
    >>> as_pure(PurePosixPath("a/b"), "windows", ValueError)
    PureWindowsPath('a/b')
    """
    target = flavor(resolve(platform))
    if isinstance(os_path, str):
        return target(str.__str__(os_path))
    if not isinstance(os_path, PurePath):
        raise TypeError(f"expected a str or a PurePath, not {type_name(os_path)}")
    if platform is None or isinstance(os_path, target):
        return os_path
    text = str(os_path)
    if os_path.anchor:
        raise error(f"cannot carry the anchored path {quote(text)} to the {target.__name__} flavor")
    if target is PureWindowsPath and any(("\\" in p or ":" in p) for p in os_path.parts):
        raise error(f"a component of {quote(text)} holds a backslash or colon, special on Windows")
    return target(*os_path.parts)
