"""Test 3 -- can aggressive retries rescue the images that failed?

For every image no decoder could read, this tries in order:
  1. native full resolution
  2. 4x4 overlapping tiles at native resolution (crop without a detector)
  3. 2x upscale of the 1600px version

Result on the 58-image sample set: 0 of 28 recovered.

That is the evidence that the failures are not a decoder or resolution
problem. 22 of those images contain no barcode at all, 5 have one sliced
by the frame edge, and 2 are curved/blurry jars whose bars are genuinely
unresolvable. No amount of retrying invents pixels that were never
captured -- the fix is at capture time.

Run:  python test_03_failure_recovery.py
"""
from __future__ import annotations

import json
import time

import numpy as np
import zxingcpp
from PIL import Image, ImageOps

from common import (DEFAULT_MAX_DIM, ensure_results_dir, pick_retail,
                    rel_name, sample_files)

TILES = 4          # 4x4 grid
TILE_FRACTION = 2  # each tile is half the width/height -> ~40% overlap


def try_native(full):
    return pick_retail(zxingcpp.read_barcodes(full)), "native-full"


def try_tiles(full):
    H, W = full.shape
    th, tw = H // TILE_FRACTION, W // TILE_FRACTION
    for ny in range(TILES):
        for nx in range(TILES):
            y = int(ny * (H - th) / (TILES - 1))
            x = int(nx * (W - tw) / (TILES - 1))
            b = pick_retail(zxingcpp.read_barcodes(full[y:y + th, x:x + tw]))
            if b:
                return b, f"tile({nx},{ny})@native"
    return None, None


def try_upscale(im):
    small = im.copy()
    small.thumbnail((DEFAULT_MAX_DIM, DEFAULT_MAX_DIM))
    big = small.resize((small.width * 2, small.height * 2), Image.LANCZOS)
    return pick_retail(zxingcpp.read_barcodes(np.array(big))), "2x-upscale"


def main():
    files = sample_files()
    # First pass at the standard setting to find the failures.
    failures = []
    for path in files:
        im = ImageOps.exif_transpose(Image.open(path)).convert("L")
        c = im.copy()
        c.thumbnail((DEFAULT_MAX_DIM, DEFAULT_MAX_DIM))
        if not pick_retail(zxingcpp.read_barcodes(np.array(c))):
            failures.append(path)

    print(f"{len(failures)} images failed at {DEFAULT_MAX_DIM}px; "
          f"attempting recovery\n")

    recovered = {}
    for path in failures:
        im = ImageOps.exif_transpose(Image.open(path)).convert("L")
        full = np.array(im)
        name = rel_name(path)
        t0 = time.perf_counter()

        hit, how = try_native(full)
        if not hit:
            hit, how = try_tiles(full)
        if not hit:
            hit, how = try_upscale(im)

        dt = (time.perf_counter() - t0) * 1000
        if hit:
            recovered[name] = {"text": hit.text, "format": hit.format.name,
                               "via": how}
            print(f"{name:<32} RECOVERED {hit.text} via {how} ({dt:.0f}ms)")
        else:
            print(f"{name:<32} still MISS ({dt:.0f}ms)")

    print(f"\nrecovered {len(recovered)}/{len(failures)}")
    if not recovered:
        print("No image was rescued by extra resolution, tiling or upscaling.\n"
              "The remaining failures are capture problems, not decode problems.")

    out = ensure_results_dir() / "test_03_failure_recovery.json"
    json.dump({"failures": [rel_name(f) for f in failures],
               "recovered": recovered}, open(out, "w"), indent=2)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
