"""Test 2 -- input resolution sweep, and does cropping to the barcode help?

Two questions this answers:
  1. What resolution should we feed the decoder?
  2. Is it worth adding a barcode-detector model to crop the ROI first?

Result on the 58-image sample set:
    800px 15 | 1000px 23 | 1200px 27 | 1600px 29 | 2000px 28 | native 27
    cropped to the barcode: 29 -- identical to just using 1600px.

So: resize to 1600px, do not crop, do not add a detector model.
zxing-cpp already localises the barcode internally (it returns the
corner coordinates, and found one covering 0.3% of a 12MP frame).

Run:  python test_02_resolution_and_crop.py
"""
from __future__ import annotations

import json
import time

import numpy as np
import zxingcpp
from PIL import Image, ImageOps

from common import (ensure_results_dir, pick_retail, rel_name, sample_files)

SIZES = [800, 1000, 1200, 1600, 2000, None]   # None = native resolution


def box_from(barcode, decoded_shape, full_width):
    """Map a decoded barcode's corner points back onto the full-res image."""
    p = barcode.position
    xs = [p.top_left.x, p.top_right.x, p.bottom_left.x, p.bottom_right.x]
    ys = [p.top_left.y, p.top_right.y, p.bottom_left.y, p.bottom_right.y]
    scale = full_width / decoded_shape[1]
    return (min(xs) * scale, min(ys) * scale,
            max(xs) * scale, max(ys) * scale)


def main():
    files = sample_files()
    stats = {str(s): {"n": 0, "ms": 0.0} for s in SIZES}
    stats["crop"] = {"n": 0, "ms": 0.0}
    detail = []

    for path in files:
        im = ImageOps.exif_transpose(Image.open(path)).convert("L")
        full = np.array(im)
        H, W = full.shape
        row = {"name": rel_name(path)}
        located = None

        for s in SIZES:
            c = im.copy()
            if s:
                c.thumbnail((s, s))
            arr = np.array(c)
            t0 = time.perf_counter()
            b = pick_retail(zxingcpp.read_barcodes(arr))
            stats[str(s)]["ms"] += (time.perf_counter() - t0) * 1000
            row[str(s)] = b.text if b else "MISS"
            if b:
                stats[str(s)]["n"] += 1
                if located is None:
                    located = (b, arr.shape)

        # Crop to the located barcode, taken from NATIVE pixels, then retry.
        if located:
            b, shape = located
            x0, y0, x1, y1 = box_from(b, shape, W)
            pad_x = (x1 - x0) * 0.08 + 10
            pad_y = (y1 - y0) * 0.08 + 10
            crop = full[max(0, int(y0 - pad_y)):min(H, int(y1 + pad_y)),
                        max(0, int(x0 - pad_x)):min(W, int(x1 + pad_x))]
            t0 = time.perf_counter()
            cb = pick_retail(zxingcpp.read_barcodes(crop))
            stats["crop"]["ms"] += (time.perf_counter() - t0) * 1000
            row["crop"] = cb.text if cb else "MISS"
            if cb:
                stats["crop"]["n"] += 1
        else:
            row["crop"] = "MISS (nothing to locate)"

        detail.append(row)
        print(f"{row['name']:<32} " +
              " ".join(f"{s or 'native'}:{'OK ' if row[str(s)] != 'MISS' else '-- '}"
                       for s in SIZES) +
              f" crop:{'OK' if row['crop'].startswith('MISS') is False else '--'}")

    n = len(files)
    print(f"\n=== zxing-cpp resolution sweep, {n} images ===")
    print(f"{'input':<16}{'decoded':<12}{'rate':<10}{'avg time'}")
    for s in SIZES:
        d = stats[str(s)]
        label = f"{s}px" if s else "native (4032)"
        print(f"{label:<16}{d['n']}/{n:<10}{100*d['n']/n:>4.0f}%   {d['ms']/n:>6.0f}ms")
    d = stats["crop"]
    print(f"{'CROPPED':<16}{d['n']}/{n:<10}{100*d['n']/n:>4.0f}%   {d['ms']/n:>6.0f}ms"
          f"   (decode only, excludes locating)")

    union = {r["name"] for r in detail
             if any(r[str(s)] != "MISS" for s in SIZES)}
    at1600 = {r["name"] for r in detail if r["1600"] != "MISS"}
    print(f"\nunion of every resolution : {len(union)}/{n}")
    print(f"1600px alone              : {len(at1600)}/{n}")
    print(f"gained by multi-scale     : {sorted(union - at1600) or 'nothing'}")

    out = ensure_results_dir() / "test_02_resolution_and_crop.json"
    json.dump(detail, open(out, "w"), indent=2)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
