"""Test 4 -- OCR the human-readable digits as a barcode fallback.

When the bars cannot be decoded, the digits printed under the barcode
(or the EAN printed in the label text) are often still readable. This
OCRs the image, pulls any 13-digit run, and validates it with the EAN-13
check digit.

Result on the 58-image sample set: 5 of 28 failures recovered --
AND ONE OF THOSE FIVE WAS WRONG. For samples1/20260829_192628.jpg the
OCR produced 8904505198366, which passes the checksum, while the true
code is 8904505983665.

The lesson: a check digit is a 1-in-10 filter, not proof of correctness.
Any OCR-recovered barcode MUST also be looked up in the product master
before it is trusted. That lookup is the real validation step.

Run:  python test_04_ocr_barcode_fallback.py
"""
from __future__ import annotations

import json
import re

import numpy as np
import zxingcpp
from PIL import Image, ImageOps
from rapidocr_onnxruntime import RapidOCR

from common import (DEFAULT_MAX_DIM, ean13_valid, ensure_results_dir,
                    pick_retail, rel_name, repair_ean13, sample_files)

OCR_MAX_DIM = 2000
ROTATIONS = (0, 90, 270)

# Codes verified by eye from the printed digits, for the images where we
# know what the answer should be. Used to catch checksum false positives.
KNOWN_TRUE = {
    "samples1/20260829_192628.jpg": "8904505983665",
}


def ean_candidates(text: str) -> set[str]:
    """Every checksum-valid 13-digit run inside an OCR line."""
    digits_only = re.sub(r"[\s\-]", "", text)
    found = set()
    for m in re.finditer(r"(?=(\d{13}))", digits_only):
        if ean13_valid(m.group(1)):
            found.add(m.group(1))
    return found


def main():
    ocr = RapidOCR()
    files = sample_files()

    failures = []
    for path in files:
        im = ImageOps.exif_transpose(Image.open(path)).convert("L")
        c = im.copy()
        c.thumbnail((DEFAULT_MAX_DIM, DEFAULT_MAX_DIM))
        if not pick_retail(zxingcpp.read_barcodes(np.array(c))):
            failures.append(path)

    print(f"Attempting OCR recovery on {len(failures)} failures\n")
    out = {}
    false_positives = []

    for path in failures:
        name = rel_name(path)
        im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        im.thumbnail((OCR_MAX_DIM, OCR_MAX_DIM))
        hits = set()
        for rot in ROTATIONS:
            res, _ = ocr(np.array(im.rotate(rot, expand=True)))
            for _box, text, _conf in (res or []):
                hits |= ean_candidates(text)
            if hits:
                break

        out[name] = sorted(hits)
        truth = KNOWN_TRUE.get(name)
        flag = ""
        if hits and truth and truth not in hits:
            flag = f"   <-- WRONG, true code is {truth}"
            false_positives.append((name, sorted(hits)[0], truth))
        print(f"{name:<32} {sorted(hits) or '-- no valid EAN-13 in text --'}{flag}")

    n_rec = sum(1 for v in out.values() if v)
    print(f"\nrecovered {n_rec}/{len(failures)} by OCR + checksum")
    print(f"of which demonstrably WRONG: {len(false_positives)}")
    for name, got, truth in false_positives:
        print(f"   {name}: OCR gave {got}, truth {truth} "
              f"(both pass the EAN-13 check digit)")
    print("\n=> Never accept an OCR-recovered barcode without a product-master lookup.")

    # Demonstrate the leading-digit repair, which is safe when the rest is clean.
    print("\n--- leading-digit repair demo ---")
    partial = "904505983665"   # OCR dropped the '8' outside the guard bar
    print(f"OCR saw 12 digits {partial!r} -> "
          f"checksum-valid completions: {repair_ean13(partial)}")

    dest = ensure_results_dir() / "test_04_ocr_barcode_fallback.json"
    json.dump({"recovered": out, "false_positives": false_positives},
              open(dest, "w"), indent=2)
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
