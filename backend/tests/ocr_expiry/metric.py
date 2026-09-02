"""Scoring for expiry-date extraction, plus shared setup.

The metric deliberately ignores date parsing and normalisation: it only asks
"does the correct expiry appear anywhere in the raw OCR output, in any form
the pack might print it". That keeps these tests measuring the OCR engine
rather than a regex.

This matters -- an earlier strict-parser metric scored 20/44 where the
engine had actually read 31/44. Sample 39, for instance, returns
`EXP2028.JAN.21`, which is exactly correct but matches no DD/MM/YYYY rule.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# The suite lives one level down from the shared helpers.
TESTS_ROOT = Path(__file__).resolve().parents[1]
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

from common import REPO_ROOT                     # noqa: E402
from ground_truth import EXPIRY_GROUND_TRUTH     # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parent / "results"

MON = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
       'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
MONFULL = ['january', 'february', 'march', 'april', 'may', 'june', 'july',
           'august', 'september', 'october', 'november', 'december']


def scored_samples() -> list[int]:
    """samples2 image numbers that have a ground-truth expiry date."""
    out = []
    for n in range(1, 50):
        if EXPIRY_GROUND_TRUTH.get(f"sample {n}.jpg"):
            out.append(n)
    return out


def image_path(n: int) -> Path:
    return REPO_ROOT / "samples2" / f"sample {n}.jpg"


def matches(truth: str, texts) -> bool:
    """True if `truth` (DD/MM/YY) appears in the OCR text in any printed form.

    Accepts the digit orderings seen on these packs (DD/MM/YYYY, MM/YYYY,
    YYYYMMDD) and month-name forms ("April 2031", "APR 31").
    """
    d, m, y = truth.split('/')
    mi = int(m)
    joined = ' '.join(texts)

    digits = re.sub(r'\D', '', joined)
    for t in (d + m + y, d + m + '20' + y, m + y, m + '20' + y,
              y + m + d, '20' + y + m + d):
        if t in digits:
            return True

    alnum = re.sub(r'[^a-z0-9]', '', joined.lower())
    for name in (MON[mi - 1], MONFULL[mi - 1]):
        if name + '20' + y in alnum or name + y in alnum:
            return True
    return False


def texts_of(ocr_result) -> list[str]:
    """RapidOCR returns [(box, text, confidence), ...] or None."""
    return [t for _box, t, _conf in (ocr_result or [])]


def ensure_results_dir() -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return RESULTS_DIR


def report(title: str, rows, n: int):
    """rows: list of (label, hits, avg_ms)."""
    print(f"\n=== {title}, {n} images ===")
    print(f"{'strategy':<34}{'correct':<13}{'rate':<9}{'avg time'}")
    for label, hits, ms in rows:
        print(f"{label:<34}{hits}/{n:<11}{100*hits/n:>4.0f}%   {ms:>7.0f}ms")
