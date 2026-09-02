"""Run the whole benchmark suite and tee the output to results/.

    python run_all.py            # barcode tests + the expiry-OCR suite
    python run_all.py 01 02      # only those barcode tests
    python run_all.py ocr        # only the expiry-OCR suite

The OCR suite is slow (~15 min on CPU); the barcode tests take seconds.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TESTS = [
    ("01", "test_01_decoder_comparison.py", "zxing-cpp vs cv2.barcode"),
    ("02", "test_02_resolution_and_crop.py", "resolution sweep + crop test"),
    ("03", "test_03_failure_recovery.py", "aggressive retry on failures"),
    ("04", "test_04_ocr_barcode_fallback.py", "OCR + checksum barcode fallback"),
]

# The expiry-OCR work lives in its own suite with its own runner.
OCR_SUITE = ("ocr", Path("ocr_expiry") / "run_ocr_tests.py",
             "expiry-date OCR suite (resolution, preprocessing, cropping)")


def main():
    wanted = sys.argv[1:]
    selected = [t for t in TESTS if not wanted or t[0] in wanted]
    if not wanted or OCR_SUITE[0] in wanted:
        selected.append(OCR_SUITE)
    (HERE / "results").mkdir(exist_ok=True)
    failed = []

    for num, script, desc in selected:
        print("\n" + "=" * 72)
        print(f"TEST {num}: {desc}")
        print("=" * 72)
        proc = subprocess.run([sys.executable, str(HERE / script)],
                              cwd=HERE, capture_output=True, text=True)
        sys.stdout.write(proc.stdout)
        if proc.returncode != 0:
            sys.stdout.write(proc.stderr)
            failed.append(script)
        log = HERE / "results" / f"test_{num}.log"
        log.write_text(proc.stdout + proc.stderr)
        print(f"\n[log: {log}]")

    print("\n" + "=" * 72)
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        sys.exit(1)
    print(f"All {len(selected)} test(s) completed.")


if __name__ == "__main__":
    main()
