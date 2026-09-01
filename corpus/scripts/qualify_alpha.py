#!/usr/bin/env python3
"""Run the Wave 11 corpus qualification gates, including repeated live checks."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "corpus/scripts"


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-pending-review", action="store_true")
    parser.add_argument("--source-checks", type=int, default=3)
    args = parser.parse_args()
    if args.source_checks < 3:
        raise SystemExit("Wave 11 qualification requires at least three consecutive live source checks")

    validator = [sys.executable, str(SCRIPTS / "validate_corpus.py")]
    if args.allow_pending_review:
        validator.append("--allow-pending-review")
    run(validator)
    run([sys.executable, str(SCRIPTS / "audit_originality.py")])

    with tempfile.TemporaryDirectory(prefix="design-wave11-source-checks-") as temp_dir:
        for index in range(1, args.source_checks + 1):
            run([
                sys.executable, str(SCRIPTS / "audit_sources.py"), "--check-only",
                "--report", str(Path(temp_dir) / f"source-check-{index}.json"),
            ])

    print(json.dumps({
        "status": "pass",
        "review_mode": "allow-pending" if args.allow_pending_review else "accepted-only",
        "consecutive_source_checks": args.source_checks,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
