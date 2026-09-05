"""Run the expiry-parser test suite.

    python run_parser_tests.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TESTS = [
    ("test_formats.py", "date formats, repair, day inference (unit)"),
    ("test_parser.py", "scored against ground truth (fixture)"),
]


def main() -> int:
    failed = []
    for script, desc in TESTS:
        print("\n" + "=" * 68)
        print(f"{script}  --  {desc}")
        print("=" * 68)
        proc = subprocess.run([sys.executable, str(HERE / script)],
                              cwd=HERE, capture_output=True, text=True)
        sys.stdout.write(proc.stdout + proc.stderr)
        if proc.returncode != 0:
            failed.append(script)
    print("\n" + "=" * 68)
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        return 1
    print("Expiry-parser suite passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
