#!/usr/bin/env python3
"""Run the shared Design research validator from the Directions skill surface."""
from pathlib import Path
import runpy

TARGET = Path(__file__).resolve().parents[3] / "scripts" / "design_research.py"
runpy.run_path(str(TARGET), run_name="__main__")
