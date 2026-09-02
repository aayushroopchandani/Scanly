"""OCR test 4 -- rotation retry, and raw OCR vs a strict date parser.

Runs RapidOCR over each image with no preprocessing and pulls out any
line that looks like a date or a date label. Where ground truth exists
(samples2, from the supplied docx) it reports whether the correct date
appears anywhere in the OCR output.

Observations from the sample set:
  * ~0.7s per image on CPU, no GPU, no preprocessing needed.
  * Four date formats appear: 04/12/2026, 18/06/2025, 20250110
    (YYYYMMDD) and "January 2027" / "April 2031" (month name + year).
  * Some packs print NO expiry at all -- only a manufacture date plus
    "best before 24 months from date of manufacture" -> must be derived.
  * One supplier printed the labels "Best Before:" and "Batch No:" and
    left them blank. OCR is right; the data does not exist.
  * Sideways text needs a rotation retry: upright OCR returned
    'EPDATE210/2027' where rot90 returned 'EAPDATE23./10/2027'.

IMPORTANT distinction this test exists to make:

    correct date present in the RAW OCR text : 31/44   (see test_03)
    correct date extracted by a strict regex : 20/44

The gap is the PARSER, not the engine. Sample 39 returns `EXP2028.JAN.21`
-- exactly right -- but matches no DD/MM/YYYY rule. Do not judge OCR
quality with a parser in the loop.

Rotation retry earns its place on sideways packs: upright OCR returned
`EPDATE210/2027` where the 90-degree rotation returned `EAPDATE23./10/2027`.

Run:  python test_04_rotation_and_parsing.py
"""
from __future__ import annotations

import json
import re
import time

import numpy as np
from PIL import Image, ImageOps

from rapidocr_onnxruntime import RapidOCR

from metric import (EXPIRY_GROUND_TRUTH, ensure_results_dir,  # noqa: F401
                    matches, texts_of)
from common import rel_name, sample_files  # noqa: E402

OCR_MAX_DIM = 1000   # per test_01: 1000px scores best
ROTATIONS = (0, 90, 180, 270)

DATE_LABEL = re.compile(
    r"(EXP|EXPIRY|BEST\s*BEFORE|BB|USE\s*BY|MFG|MFD|MANUF|IMPORT|BATCH|LOT)",
    re.I)
DATE_VALUE = re.compile(
    r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}"      # 04/12/2026
    r"|\d{1,2}[/\-.]\d{4}"                      # 08/2027
    r"|\d{8}"                                   # 20250110
    r"|(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\.?\s*\d{4})",
    re.I)

MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"])}


def normalise(text: str) -> set[str]:
    """Turn any recognised date form into DD/MM/YY for comparison."""
    out = set()
    t = text.strip()
    m = re.search(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})", t)
    if m:
        d, mo, y = m.groups()
        y = y[-2:]
        out.add(f"{int(d):02d}/{int(mo):02d}/{y}")
    m = re.search(r"(\d{4})(\d{2})(\d{2})", t)
    if m:
        y, mo, d = m.groups()
        out.add(f"{int(d):02d}/{int(mo):02d}/{y[-2:]}")
    m = re.search(r"([A-Za-z]{3,9})\.?\s*(\d{4})", t)
    if m and m.group(1)[:3].lower() in MONTHS:
        mo = MONTHS[m.group(1)[:3].lower()]
        out.add(f"--/{mo:02d}/{m.group(2)[-2:]}")   # month-year only
    return out


def main():
    ocr = RapidOCR()
    files = sample_files()
    rows = []
    total_ms = 0.0

    for path in files:
        name = rel_name(path)
        im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        im.thumbnail((OCR_MAX_DIM, OCR_MAX_DIM))

        t0 = time.perf_counter()
        res, _ = ocr(np.array(im))
        lines = [t for _b, t, _c in (res or [])]
        all_lines = list(lines)
        interesting = [t for t in lines
                       if DATE_LABEL.search(t) or DATE_VALUE.search(t)]

        # Rotation retry when nothing date-like turned up.
        used_rot = 0
        if not any(DATE_VALUE.search(t) for t in interesting):
            for rot in ROTATIONS[1:]:
                res, _ = ocr(np.array(im.rotate(rot, expand=True)))
                lines = [t for _b, t, _c in (res or [])]
                all_lines += lines
                cand = [t for t in lines
                        if DATE_LABEL.search(t) or DATE_VALUE.search(t)]
                if any(DATE_VALUE.search(t) for t in cand):
                    interesting, used_rot = cand, rot
                    break
        dt = (time.perf_counter() - t0) * 1000
        total_ms += dt

        found = set()
        for t in interesting:
            found |= normalise(t)

        truth = EXPIRY_GROUND_TRUTH.get(path.split("/")[-1])
        if truth is None:
            verdict = "no ground truth / none printed"
        elif truth in found:
            verdict = "MATCH"
        elif f"--/{truth[3:]}" in found:
            verdict = "MATCH (month-year)"
        else:
            verdict = "not matched"

        rows.append(dict(name=name, rotation=used_rot, ms=dt, truth=truth,
                         extracted=sorted(found), lines=interesting,
                         all_lines=all_lines,
                         verdict=verdict))
        rot_note = f" rot{used_rot}" if used_rot else ""
        print(f"\n### {name} ({dt:.0f}ms{rot_note}) -> {verdict}"
              f"{'  truth=' + truth if truth else ''}")
        for t in interesting[:8]:
            print(f"    {t}")

    n = len(rows)
    scored = [r for r in rows if r["truth"]]
    matched = [r for r in scored if r["verdict"].startswith("MATCH")]
    print(f"\n=== expiry OCR over {n} images ===")
    print(f"avg {total_ms/n:.0f}ms per image")
    # Score against EVERY OCR line, not just the date-ish ones -- otherwise
    # the pre-filter silently discards correct reads and understates the engine.
    raw = [r for r in scored if matches(r["truth"], r["all_lines"])]
    print(f"strict-parser match  : {len(matched)}/{len(scored)}")
    print(f"present in RAW text  : {len(raw)}/{len(scored)}   "
          f"<- the engine's real score; the gap is the parser")
    print("Note: a 'not matched' here is often the pack itself -- several "
          "print only a manufacture date, or leave the field blank.")

    out = ensure_results_dir() / "ocr_test_04_rotation_and_parsing.json"
    json.dump(rows, open(out, "w"), indent=2)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
