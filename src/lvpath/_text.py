"""Short, safe renderings of caller values for error messages."""

from __future__ import annotations

_LIMIT = 40


def quote(value: object) -> str:
    """``repr`` of a string cut to 40 characters, so a huge input never floods a message.

    >>> quote("C:file")
    "'C:file'"
    >>> quote("x" * 100)
    "'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' (first 40 of 100 characters)"
    """
    text = str.__str__(value) if isinstance(value, str) else type_name(value)
    if len(text) <= _LIMIT:
        return repr(text)
    return f"{text[:_LIMIT]!r} (first {_LIMIT} of {len(text)} characters)"


def type_name(value: object) -> str:
    """The class name of ``value``, cut to 40 characters.

    >>> type_name(3)
    'int'
    """
    name = type(value).__name__
    return name if len(name) <= _LIMIT else name[:_LIMIT] + "..."
