#!/usr/bin/env python3
"""Skill-local launcher for the canonical Design state controller."""

from __future__ import annotations

import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_DIR = PLUGIN_ROOT / "scripts"
if not (RUNTIME_DIR / "design_state_cli.py").is_file():
    raise SystemExit(f"Design state runtime is missing from {RUNTIME_DIR}")
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

from design_state_commands import *  # noqa: F401,F403,E402
from design_state_cli import build_parser, main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
