"""Command-line interface for LabVIEW path strings and the flattened path form.

``lvpath to-native`` turns LabVIEW's portable path string (``/C/DIR1/DIR2``) into
a native path; ``lvpath to-labview`` does the reverse. ``lvpath decode`` turns the
hex of a flattened ``PTH0`` byte string into a native path; ``lvpath encode``
turns a native path into that hex. A value lvpath refuses exits with status
``1`` and a usage mistake with status ``2``, each with one short line on
standard error. ``python -m lvpath`` runs the same command.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import sys
from collections.abc import Sequence
from typing import NoReturn

from . import __version__
from ._flatbridge import from_flat_path, to_flat_path
from ._portable import from_portable_path, to_portable_path

_EXAMPLES = """\
examples:
  # LabVIEW's portable path string, as written in .ini and .lvproj files, to Windows.
  lvpath to-native --platform windows "/C/Program Files (x86)/Arduino"
  # prints C:\\Program Files (x86)\\Arduino

  # A UNC share and a relative path.
  lvpath to-native --platform windows //server/share/dir
  lvpath to-native --platform windows "../builds/Main Application"

  # A native Windows path to the portable string LabVIEW writes.
  lvpath to-labview --platform windows "C:\\DIR1\\DIR2"
  # prints /C/DIR1/DIR2

  # Decode the NI C:\\File flattened example into a path.
  lvpath decode --platform windows 505448300000000b0000000201430466696c65

  # Encode a path into its flattened hex form (spaces in the hex are accepted on decode).
  lvpath encode --platform posix /usr/local/bin
"""

_COMMANDS = [
    (
        "to-native",
        "text",
        "a LabVIEW portable path string to a native path",
        "Convert a LabVIEW portable path string (/C/DIR1/DIR2, //server/share, a/b) "
        "into a native path. An empty string is <Not A Path> and is an error.",
    ),
    (
        "to-labview",
        "path",
        "a native path to a LabVIEW portable path string",
        "Convert a native path into the portable path string LabVIEW writes into "
        "configuration and project files. An empty path prints an empty line, "
        "LabVIEW's <Not A Path>.",
    ),
    (
        "decode",
        "hex",
        "hex of flattened PTH0 bytes to a native path",
        "Decode the hex of a flattened PTH0 byte string into a native path.",
    ),
    (
        "encode",
        "path",
        "a native path to flattened PTH0 hex",
        "Encode a native path into the hex of its flattened PTH0 byte string.",
    ),
]

_MESSAGE_LIMIT = 200


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        # argparse echoes the offending argument; keep the line short whatever it was.
        if sys.stderr is not None:
            with contextlib.suppress(OSError, ValueError):
                self.print_usage(sys.stderr)
        _say(f"{self.prog}: error: {message}")
        raise SystemExit(2)


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="lvpath",
        description=(
            "Convert LabVIEW's portable path strings to and from native paths, and decode "
            "or encode the LabVIEW PTH0 flattened path form."
        ),
        epilog=_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"lvpath {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    for name, argument, short, long in _COMMANDS:
        sub = subparsers.add_parser(name, help=short, description=long)
        sub.add_argument(argument, help=f"the {argument} to convert")
        sub.add_argument(
            "--platform",
            choices=["windows", "posix"],
            default=None,
            help="native path flavor to use (default: the current operating system)",
        )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line interface and return the process exit status.

    >>> main(["to-labview", "--platform", "windows", "C:/DIR1/DIR2"])
    /C/DIR1/DIR2
    0
    """
    for stream in (sys.stdout, sys.stderr):
        # Paths may hold any character; a Windows pipe defaults to a legacy code page.
        # Undecodable POSIX arguments arrive as lone surrogates; write their bytes back.
        if isinstance(stream, io.TextIOWrapper):
            with contextlib.suppress(OSError, ValueError):
                stream.reconfigure(encoding="utf-8", errors="surrogateescape")
    try:
        args = _build_parser().parse_args(argv)
    except SystemExit as stop:
        return stop.code if isinstance(stop.code, int) else 2
    try:
        result = _run(args.command, args, args.platform)
    except ValueError as error:
        _say(f"lvpath: {error}")
        return 1
    if sys.stdout is None:
        return 1
    try:
        sys.stdout.write(result + "\n")
        sys.stdout.flush()
    except OSError:
        # The reader went away (Windows reports EINVAL, POSIX EPIPE); point stdout at
        # nothing so the flush at interpreter exit stays quiet.
        with contextlib.suppress(OSError, ValueError):
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 1
    return 0


def _run(command: str, args: argparse.Namespace, platform: str | None) -> str:
    if command == "to-native":
        return str(from_portable_path(args.text, platform=platform))
    if command == "to-labview":
        return to_portable_path(args.path, platform=platform)
    if command == "decode":
        return str(from_flat_path(_hex_bytes(args.hex), platform=platform))
    return to_flat_path(args.path, platform=platform).hex()


def _hex_bytes(raw_hex: str) -> bytes:
    try:
        return bytes.fromhex(raw_hex.replace(" ", ""))
    except ValueError:
        raise ValueError(f"not valid hex ({len(raw_hex)} characters given)") from None


def _say(line: str) -> None:
    if len(line) > _MESSAGE_LIMIT:
        line = line[: _MESSAGE_LIMIT - 3] + "..."
    if sys.stderr is None:
        return
    with contextlib.suppress(OSError, ValueError):
        print(line, file=sys.stderr)
