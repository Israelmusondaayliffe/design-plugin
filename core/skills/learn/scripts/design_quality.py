#!/usr/bin/env python3
"""Run the shared Design quality controller from the Learn skill."""
from pathlib import Path
import runpy

TARGET = Path(__file__).resolve().parents[3] / "scripts" / "design_quality.py"
runpy.run_path(str(TARGET), run_name="__main__")
