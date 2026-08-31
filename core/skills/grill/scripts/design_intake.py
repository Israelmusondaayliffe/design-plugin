#!/usr/bin/env python3
"""Skill-local launcher for the canonical Design intake helper."""
from __future__ import annotations
import runpy
from pathlib import Path
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
TARGET = PLUGIN_ROOT / "scripts" / "design_intake.py"
if not TARGET.is_file():
    raise SystemExit(f"Design intake runtime is missing from {TARGET}")
runpy.run_path(str(TARGET), run_name="__main__")
