"""Run the expiry-OCR suite.

    python run_ocr_tests.py          # all tests
    python run_ocr_tests.py 01 03    # selected

Each test writes JSON into results/ and a log alongside it.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TESTS = [
    ("01", "test_01_resolution_sweep.py", "input resolution sweep"),
    ("02", "test_02_preprocessing.py", "preprocessing variants"),
    ("03", "test_03_crop_strategies.py", "whole image vs cropping (headline)"),
    ("04", "test_04_rotation_and_parsing.py", "rotation retry; raw vs parsed"),
]


def main():
    wanted = sys.argv[1:]
    selected = [t for t in TESTS if not wanted or t[0] in wanted]
    (HERE / "results").mkdir(exist_ok=True)
    failed = []

    for num, script, desc in selected:
        print("\n" + "=" * 72)
        print(f"OCR TEST {num}: {desc}")
        print("=" * 72)
        proc = subprocess.run([sys.executable, str(HERE / script)],
                              cwd=HERE, capture_output=True, text=True)
        sys.stdout.write(proc.stdout)
        if proc.returncode != 0:
            sys.stdout.write(proc.stderr)
            failed.append(script)
        (HERE / "results" / f"ocr_test_{num}.log").write_text(
            proc.stdout + proc.stderr)

    print("\n" + "=" * 72)
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        sys.exit(1)
    print(f"All {len(selected)} OCR test(s) completed.")


if __name__ == "__main__":
    main()
