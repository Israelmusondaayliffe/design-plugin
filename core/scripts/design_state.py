#!/usr/bin/env python3
"""Durable workflow state controller for the Design plugin.

Standard-library only. Installs nothing, accesses no network, and writes state atomically.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from design_state_commands import *  # noqa: F401,F403,E402
from design_state_cli import build_parser, main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
