"""Command-line interface for the LabVIEW flattened path form.

``lvpath decode`` turns the hex of a flattened ``PTH0`` byte string into an OS
path; ``lvpath encode`` turns an OS path into that hex. Errors are written to
standard error and the process exits with status ``1``.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from . import __version__
from ._flatbridge import from_flat_path, to_flat_path
from ._flatten import FlatPathError

_EXAMPLES = """\
examples:
  # Decode the NI C:\\File flattened example into a path.
  lvpath decode --platform windows 505448300000000b0000000201430466696c65

  # Encode a Windows path into its flattened hex form.
  lvpath encode --platform windows "C:\\file"

  # Encode a POSIX path (spaces in the hex are accepted on decode).
  lvpath encode --platform posix /usr/local/bin
"""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lvpath",
        description="Decode and encode the LabVIEW PTH0 flattened path form.",
        epilog=_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"lvpath {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    decode = subparsers.add_parser(
        "decode",
        help="hex of flattened PTH0 bytes to an OS path",
        description="Decode the hex of a flattened PTH0 byte string into an OS path.",
    )
    decode.add_argument("hex", help="flattened path bytes as hex (spaces allowed)")
    _add_platform(decode)

    encode = subparsers.add_parser(
        "encode",
        help="an OS path to flattened PTH0 hex",
        description="Encode an OS path into the hex of its flattened PTH0 byte string.",
    )
    encode.add_argument("path", help="the OS path to flatten")
    _add_platform(encode)
    return parser


def _add_platform(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--platform",
        choices=["windows", "posix"],
        default=None,
        help="path flavor to use (default: the current operating system)",
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line interface. Returns the process exit status."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "decode":
            print(_decode(args.hex, args.platform))
        else:
            print(_encode(args.path, args.platform))
    except (FlatPathError, ValueError) as error:
        print(f"lvpath: {error}", file=sys.stderr)
        return 1
    return 0


def _decode(raw_hex: str, platform: str | None) -> str:
    try:
        data = bytes.fromhex(raw_hex.replace(" ", ""))
    except ValueError as error:
        raise ValueError(f"not valid hex: {error}") from error
    return str(from_flat_path(data, platform=platform))


def _encode(path: str, platform: str | None) -> str:
    return to_flat_path(path, platform=platform).hex()


if __name__ == "__main__":
    sys.exit(main())
