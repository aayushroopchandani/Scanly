"""OCR test 3 -- should we crop to the expiry region before running OCR?

THE HEADLINE TEST. Compares feeding the whole photo against three ways of
cropping first, including a hand-drawn "perfect" crop of the date panel.

Result on the 44 ground-truth images:
    A  whole image @1000px                 31/44  (70%)
    A+ whole image @1000px + unsharp       33/44  (75%)   <- best
    B  two-pass: OCR-located box, re-OCR   31/44  (70%)   no change, 5x slower
    D1 manual date-panel crop -> 1000px    25/44  (57%)
    D2 manual date-panel crop, native res  24/44  (55%)

Cropping LOSES accuracy, even when a human places the box perfectly.

Two mechanisms, both visible in the per-image output:

  1. The text detector collapses on crops. Sample 1: 56 text boxes found in
     the whole image, 7 in the crop -- and the MFG/EXP lines were missed
     entirely despite being fully inside the crop, nothing clipped.
     Sample 4: 13 boxes -> 3 boxes of garbage.

  2. Recognition degrades on over-magnified text. Sample 48 reads
     ":23/07/2027" from the whole image but "X : 23.0712027" from the crop.

DBNet is trained on full photographs. Cropping to ~24% of the frame makes
text occupy far more of the image than anything in its training
distribution, so detection quality drops.

Practical conclusion: feed the whole image. Do not build a date-region
detector -- a perfect one would still make things worse.

Run:  python test_03_crop_strategies.py
"""
from __future__ import annotations

import json
import re
import time

import cv2
import numpy as np
from PIL import Image, ImageOps
from rapidocr_onnxruntime import RapidOCR

from date_panel_boxes import BOX
from metric import (EXPIRY_GROUND_TRUTH, ensure_results_dir, image_path,
                    matches, report, scored_samples, texts_of)

MAX_DIM = 1000
DATEISH = re.compile(
    r'(EXP|EXPIRY|BEST|BB|USE|MFG|MFD|MANUF|IMPORT|BATCH|LOT'
    r'|\d{1,2}[/\-.]\d|\d{4}'
    r'|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', re.I)


def unsharp(a):
    return cv2.addWeighted(a, 1.6, cv2.GaussianBlur(a, (0, 0), 2.0), -0.6, 0)


def two_pass(ocr, base, first_result, first_size):
    """Crop to each date-ish box the first pass found, re-OCR at native res."""
    W0, H0 = base.size
    texts = texts_of(first_result)
    scale = W0 / first_size[0]
    for box, txt, _c in (first_result or []):
        if not DATEISH.search(txt):
            continue
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        x0, y0 = min(xs) * scale, min(ys) * scale
        x1, y1 = max(xs) * scale, max(ys) * scale
        pw, ph = (x1 - x0) * 0.15 + 25, (y1 - y0) * 0.9 + 25
        cx0, cy0 = max(0, int(x0 - pw)), max(0, int(y0 - ph))
        cx1, cy1 = min(W0, int(x1 + pw)), min(H0, int(y1 + ph))
        if cx1 - cx0 < 20 or cy1 - cy0 < 12:
            continue
        crop = base.crop((cx0, cy0, cx1, cy1))
        if crop.width < 700:
            k = min(3.0, 700 / max(crop.width, 1))
            crop = crop.resize((int(crop.width * k), int(crop.height * k)),
                               Image.LANCZOS)
        res, _ = ocr(np.array(crop))
        texts += texts_of(res)
    return texts


NAMES = ["A  whole @1000px", "A+ whole @1000px + unsharp",
         "B  two-pass (OCR-located box)", "D1 manual crop -> 1000px",
         "D2 manual crop, native res"]


def main():
    ocr = RapidOCR()
    nums = [n for n in scored_samples() if n in BOX]
    hits = {k: 0 for k in NAMES}
    ms = {k: 0.0 for k in NAMES}
    per = {k: set() for k in NAMES}

    for n in nums:
        truth = EXPIRY_GROUND_TRUTH[f"sample {n}.jpg"]
        base = ImageOps.exif_transpose(Image.open(image_path(n))).convert("RGB")
        W, H = base.size
        x0, y0, x1, y1 = BOX[n]
        panel = base.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)))

        whole = base.copy()
        whole.thumbnail((MAX_DIM, MAX_DIM))
        wa = np.array(whole)
        small_panel = panel.copy()
        small_panel.thumbnail((MAX_DIM, MAX_DIM))

        # A
        t0 = time.perf_counter()
        res_a, _ = ocr(wa)
        ms[NAMES[0]] += (time.perf_counter() - t0) * 1000
        if matches(truth, texts_of(res_a)):
            hits[NAMES[0]] += 1
            per[NAMES[0]].add(n)

        # A+
        t0 = time.perf_counter()
        res, _ = ocr(unsharp(wa))
        ms[NAMES[1]] += (time.perf_counter() - t0) * 1000
        if matches(truth, texts_of(res)):
            hits[NAMES[1]] += 1
            per[NAMES[1]].add(n)

        # B
        t0 = time.perf_counter()
        txt_b = two_pass(ocr, base, res_a, whole.size)
        ms[NAMES[2]] += (time.perf_counter() - t0) * 1000
        if matches(truth, txt_b):
            hits[NAMES[2]] += 1
            per[NAMES[2]].add(n)

        # D1 / D2
        for name, img in ((NAMES[3], np.array(small_panel)),
                          (NAMES[4], np.array(panel))):
            t0 = time.perf_counter()
            res, _ = ocr(img)
            ms[name] += (time.perf_counter() - t0) * 1000
            if matches(truth, texts_of(res)):
                hits[name] += 1
                per[name].add(n)

        print(f"sample {n:<3} " +
              "  ".join(f"{k.split()[0]}:{'O' if n in per[k] else '.'}"
                        for k in NAMES) + f"   {truth}")

    N = len(nums)
    report("whole image vs cropping strategies",
           [(k, hits[k], ms[k] / N) for k in NAMES], N)

    base_set = per[NAMES[0]]
    print()
    for k in NAMES[1:]:
        print(f"{k:<30} gained {sorted(per[k]-base_set)}  "
              f"lost {sorted(base_set-per[k])}")

    area = sum((BOX[n][2]-BOX[n][0]) * (BOX[n][3]-BOX[n][1]) for n in nums) / N
    print(f"\nmanual crops keep on average {100*area:.0f}% of the frame area")

    out = ensure_results_dir() / "ocr_test_03_crop_strategies.json"
    json.dump({k: sorted(v) for k, v in per.items()}, open(out, "w"), indent=1)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
