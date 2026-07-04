#!/usr/bin/env python3
"""Run PetGenesis tests without writing bytecode or pytest cache files."""

from __future__ import annotations

import os
import sys


def main() -> int:
    sys.dont_write_bytecode = True
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

    import pytest

    args = sys.argv[1:] or ["tests"]
    return pytest.main(["-p", "no:cacheprovider", *args])


if __name__ == "__main__":
    raise SystemExit(main())
