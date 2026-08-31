#!/usr/bin/env python3
"""Run the shared Design system compiler from the Design MD skill surface."""
from pathlib import Path
import runpy

TARGET = Path(__file__).resolve().parents[3] / "scripts" / "design_system.py"
runpy.run_path(str(TARGET), run_name="__main__")
