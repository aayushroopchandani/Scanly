"""OCR test 2 -- does classical preprocessing help, or hurt?

Result on the 44 ground-truth images (all at 1000px):
    baseline 31 | grayscale 31 | unsharp 33 | denoise 31
    CLAHE 28    | CLAHE+unsharp 26 | adaptive threshold 19

Only mild sharpening helps (+2, nothing lost, no extra cost). Everything
else is neutral or harmful, and adaptive threshold is catastrophic (-12).

Why: PP-OCR's detector and recogniser are trained on natural colour
photographs. Binarisation and heavy contrast stretching throw away the
gradients and texture the network expects, pushing the input out of
distribution. This is the opposite of what classical OCR (Tesseract)
wants, which is why the original architecture proposal -- written around
Tesseract -- recommends thresholding.

Run:  python test_02_preprocessing.py
"""
from __future__ import annotations

import json
import time

import cv2
import numpy as np
from PIL import Image, ImageOps
from rapidocr_onnxruntime import RapidOCR

from metric import (EXPIRY_GROUND_TRUTH, ensure_results_dir, image_path,
                    matches, report, scored_samples, texts_of)

MAX_DIM = 1000


def v_none(a):
    return a


def v_gray(a):
    g = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY)
    return cv2.cvtColor(g, cv2.COLOR_GRAY2RGB)


def v_clahe(a):
    lab = cv2.cvtColor(a, cv2.COLOR_RGB2LAB)
    l, u, v = cv2.split(lab)
    l = cv2.createCLAHE(2.0, (8, 8)).apply(l)
    return cv2.cvtColor(cv2.merge((l, u, v)), cv2.COLOR_LAB2RGB)


def v_unsharp(a):
    return cv2.addWeighted(a, 1.6, cv2.GaussianBlur(a, (0, 0), 2.0), -0.6, 0)


def v_threshold(a):
    g = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY)
    t = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                              cv2.THRESH_BINARY, 31, 10)
    return cv2.cvtColor(t, cv2.COLOR_GRAY2RGB)


def v_clahe_unsharp(a):
    return v_unsharp(v_clahe(a))


def v_denoise(a):
    return cv2.fastNlMeansDenoisingColored(a, None, 5, 5, 7, 21)


VARIANTS = [
    ("baseline (none)", v_none),
    ("grayscale", v_gray),
    ("unsharp mask", v_unsharp),
    ("denoise", v_denoise),
    ("CLAHE", v_clahe),
    ("CLAHE + unsharp", v_clahe_unsharp),
    ("adaptive threshold", v_threshold),
]


def main():
    ocr = RapidOCR()
    nums = scored_samples()
    hits = {k: 0 for k, _ in VARIANTS}
    ms = {k: 0.0 for k, _ in VARIANTS}
    per = {k: set() for k, _ in VARIANTS}

    for n in nums:
        truth = EXPIRY_GROUND_TRUTH[f"sample {n}.jpg"]
        im = ImageOps.exif_transpose(Image.open(image_path(n))).convert("RGB")
        im.thumbnail((MAX_DIM, MAX_DIM))
        arr = np.array(im)
        for name, fn in VARIANTS:
            t0 = time.perf_counter()
            res, _ = ocr(fn(arr))
            ms[name] += (time.perf_counter() - t0) * 1000
            if matches(truth, texts_of(res)):
                hits[name] += 1
                per[name].add(n)
        print(f"sample {n:<3} " +
              ''.join('O' if n in per[k] else '.' for k, _ in VARIANTS) +
              f"   truth={truth}")

    N = len(nums)
    report(f"preprocessing variants @{MAX_DIM}px",
           [(k, hits[k], ms[k] / N) for k, _ in VARIANTS], N)

    base = per["baseline (none)"]
    print()
    for k, _ in VARIANTS[1:]:
        print(f"{k:<24} gained {sorted(per[k]-base)}  lost {sorted(base-per[k])}")

    out = ensure_results_dir() / "ocr_test_02_preprocessing.json"
    json.dump({k: sorted(v) for k, v in per.items()}, open(out, "w"), indent=1)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
