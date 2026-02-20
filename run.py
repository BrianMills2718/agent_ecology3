#!/usr/bin/env python3
"""Convenience wrapper for `python run.py` local usage."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_ecology3.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
