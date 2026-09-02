"""OCR test 1 -- what input resolution should the image be fed at?

Result on the 44 ground-truth images:
    1000px 31 | 1600px 28 | 2200px 25 | 3000px 26 | native 22

Lower resolution wins, and native is both the worst and 5x slower.
Downscaling suppresses packaging texture, gloss and background clutter
that otherwise generate spurious text detections.

Run:  python test_01_resolution_sweep.py
"""
from __future__ import annotations

import json
import time

import numpy as np
from PIL import Image, ImageOps
from rapidocr_onnxruntime import RapidOCR

from metric import (EXPIRY_GROUND_TRUTH, ensure_results_dir, image_path,
                    matches, report, scored_samples, texts_of)

SIZES = [1000, 1600, 2200, 3000, None]   # None = native


def main():
    ocr = RapidOCR()
    nums = scored_samples()
    hits = {str(s): 0 for s in SIZES}
    ms = {str(s): 0.0 for s in SIZES}
    per = {}

    for n in nums:
        truth = EXPIRY_GROUND_TRUTH[f"sample {n}.jpg"]
        base = ImageOps.exif_transpose(Image.open(image_path(n))).convert("RGB")
        per[n] = {}
        for s in SIZES:
            im = base.copy()
            if s:
                im.thumbnail((s, s))
            t0 = time.perf_counter()
            res, _ = ocr(np.array(im))
            ms[str(s)] += (time.perf_counter() - t0) * 1000
            ok = matches(truth, texts_of(res))
            hits[str(s)] += ok
            per[n][str(s)] = ok
        marks = ''.join('O' if per[n][str(s)] else '.' for s in SIZES)
        print(f"sample {n:<3} {marks}   truth={truth}")

    N = len(nums)
    report("RapidOCR resolution sweep",
           [(f"{s}px" if s else "native (4032)", hits[str(s)], ms[str(s)] / N)
            for s in SIZES], N)

    union = sum(1 for v in per.values() if any(v.values()))
    print(f"\nunion of every resolution : {union}/{N}")
    print(f"best single resolution    : "
          f"{max(hits, key=hits.get)}px ({max(hits.values())}/{N})")

    out = ensure_results_dir() / "ocr_test_01_resolution.json"
    json.dump(per, open(out, "w"), indent=1)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
