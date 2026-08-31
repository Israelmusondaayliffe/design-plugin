#!/usr/bin/env python3
"""Run the shared Design build-wave controller from the skill surface."""
from pathlib import Path
import runpy

TARGET = Path(__file__).resolve().parents[3] / "scripts" / "design_build.py"
runpy.run_path(str(TARGET), run_name="__main__")
