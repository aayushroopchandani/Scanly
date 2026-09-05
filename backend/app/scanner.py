"""scan(image_path) -> dict

One photograph in; barcode(s), raw OCR text, and a normalised expiry
date out. No database, no HTTP.

The two extractors run SEQUENTIALLY and independently. Threading them
would save ~20ms of a ~420ms request (the OCR dominates) while adding
async machinery and competing with onnxruntime's own thread pool under
load. A try/except around each gives the same failure isolation for
none of the cost.

    python -m app.scanner "samples2/sample 5.jpg"
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from . import barcode as barcode_mod
from . import imaging
from . import ocr as ocr_mod
from .expiry import parse as parse_expiry

REPO_ROOT = Path(__file__).resolve().parents[2]


def scan(image_path: str | Path) -> dict:
    """Extract barcodes and raw text from one photograph."""
    started = time.perf_counter()

    src = imaging.load(image_path)

    # Barcode first: it is ~20x faster, so a hard failure surfaces early.
    gray, bscale = imaging.for_barcode(src)
    barcode = barcode_mod.decode(gray, bscale, src.width, src.height)

    rgb, _oscale = imaging.for_ocr(src)
    ocr = ocr_mod.extract(rgb)

    # Deterministic rules only -- same text always gives the same date,
    # and the result names the pattern that produced it.
    expiry = parse_expiry(ocr["lines"])

    try:
        shown = str(src.path.relative_to(REPO_ROOT))
    except ValueError:
        shown = str(src.path)

    return {
        "image": shown,
        "image_size": {"w": src.width, "h": src.height},
        "barcode": barcode,
        "ocr": ocr,
        "expiry": expiry.as_dict(),
        "ms_total": round((time.perf_counter() - started) * 1000, 1),
    }


def _resolve(arg: str) -> Path:
    """Accept an absolute path or one relative to the repo root."""
    p = Path(arg)
    return p if p.is_absolute() or p.exists() else REPO_ROOT / arg


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 2

    # Load the OCR models before timing anything, so the reported ms is the
    # real per-image cost and not a one-off model load. A server does this
    # once at startup; here the CLI does it once per invocation.
    load_s = ocr_mod.warmup()
    print(f"# OCR models ready in {load_s}s (one-time)", file=sys.stderr)

    result = scan(_resolve(argv[0]))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
