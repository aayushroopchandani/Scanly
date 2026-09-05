"""Cache the OCR output for every sample image.

The parser tests run against this fixture rather than re-running OCR, so
they are fast, deterministic, and measure the PARSER rather than OCR
variance. Regenerate only when the OCR settings change:

    python make_fixture.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parents[1]
BACKEND = TESTS_ROOT.parent
for p in (str(TESTS_ROOT), str(BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app import imaging, ocr                      # noqa: E402
from common import rel_name, sample_files         # noqa: E402

OUT = Path(__file__).resolve().parent / "fixtures" / "ocr_lines.json"


def main() -> None:
    print(f"loading OCR models... ({ocr.warmup()}s)")
    data = {}
    files = sample_files()
    for i, path in enumerate(files, 1):
        src = imaging.load(path)
        rgb, _ = imaging.for_ocr(src)
        result = ocr.extract(rgb)
        data[rel_name(path)] = result["lines"]
        print(f"  [{i:2d}/{len(files)}] {rel_name(path):<32} "
              f"{result['line_count']:3d} lines")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump(data, open(OUT, "w"), indent=1, ensure_ascii=False)
    print(f"\nwrote {OUT}  ({len(data)} images)")


if __name__ == "__main__":
    main()
