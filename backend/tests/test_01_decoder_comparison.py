"""Test 1 -- zxing-cpp vs cv2.barcode, head to head.

Runs both decoders over every sample image at the same input resolution
and reports decode rate, speed, disagreements and false positives.

Result on the 58-image sample set:
    zxing-cpp    29/58 overall, 29/31 on images that contain a barcode
    cv2.barcode  21/58 overall, 21/31
    cv2 never decoded an image that zxing missed.

Run:  python test_01_decoder_comparison.py
"""
from __future__ import annotations

import json
import time

import cv2
import zxingcpp

from common import (DEFAULT_MAX_DIM, ensure_results_dir, load_gray,
                    pick_retail, rel_name, sample_files)
from ground_truth import classify


def decode_zxing(img):
    t0 = time.perf_counter()
    res = zxingcpp.read_barcodes(img)
    dt = (time.perf_counter() - t0) * 1000
    best = pick_retail(res)
    return (best.text if best else None), len(res), dt


def decode_cv2(detector, img):
    t0 = time.perf_counter()
    try:
        ok, info, _types, _pts = detector.detectAndDecodeWithType(img)
        text = info[0] if (ok and info and info[0]) else None
    except cv2.error:
        text = None
    dt = (time.perf_counter() - t0) * 1000
    return text, dt


def main():
    files = sample_files()
    detector = cv2.barcode.BarcodeDetector()
    rows = []
    zx_ms = cv_ms = 0.0

    print(f"Decoding {len(files)} images at {DEFAULT_MAX_DIM}px\n")
    for path in files:
        img = load_gray(path, DEFAULT_MAX_DIM)
        z, n_found, dz = decode_zxing(img)
        c, dc = decode_cv2(detector, img)
        zx_ms += dz
        cv_ms += dc
        name = rel_name(path)
        rows.append(dict(name=name, category=classify(name), zxing=z,
                         zxing_n=n_found, cv2=c, zxing_ms=dz, cv2_ms=dc))
        print(f"{name:<32} zxing={z or 'MISS':<16}{dz:5.0f}ms   "
              f"cv2={c or 'MISS':<16}{dc:5.0f}ms")

    n = len(rows)
    zn = sum(1 for r in rows if r["zxing"])
    cn = sum(1 for r in rows if r["cv2"])
    print(f"\n=== overall ({n} images) ===")
    print(f"zxing-cpp    {zn}/{n} ({100*zn/n:.0f}%)   avg {zx_ms/n:.0f}ms")
    print(f"cv2.barcode  {cn}/{n} ({100*cn/n:.0f}%)   avg {cv_ms/n:.0f}ms")

    print("\n=== by category ===")
    for cat in ("full_barcode", "cut_off", "no_barcode"):
        sel = [r for r in rows if r["category"] == cat]
        if not sel:
            continue
        z = sum(1 for r in sel if r["zxing"])
        c = sum(1 for r in sel if r["cv2"])
        label = {"full_barcode": "barcode fully in frame",
                 "cut_off": "barcode cut off by edge",
                 "no_barcode": "no barcode in photo"}[cat]
        note = "  <- false positives" if cat == "no_barcode" else ""
        print(f"{label:<26} zxing {z}/{len(sel):<6} cv2 {c}/{len(sel)}{note}")

    zonly = [r["name"] for r in rows if r["zxing"] and not r["cv2"]]
    conly = [r["name"] for r in rows if r["cv2"] and not r["zxing"]]
    disagree = [(r["name"], r["zxing"], r["cv2"]) for r in rows
                if r["zxing"] and r["cv2"] and r["zxing"] != r["cv2"]]
    multi = [(r["name"], r["zxing_n"]) for r in rows if r["zxing_n"] > 1]
    print(f"\nzxing-only wins ({len(zonly)}): {zonly}")
    print(f"cv2-only wins   ({len(conly)}): {conly}")
    print(f"disagreements   ({len(disagree)}): {disagree}")
    print(f"multi-barcode images ({len(multi)}): {multi}")

    out = ensure_results_dir() / "test_01_decoder_comparison.json"
    json.dump(rows, open(out, "w"), indent=2)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
