"""Run the ``lvpath`` command with ``python -m lvpath``."""

from __future__ import annotations

import sys

from ._cli import main

if __name__ == "__main__":
    sys.exit(main())
