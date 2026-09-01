"""Shared helpers for the barcode / OCR benchmark suite.

Everything here is deliberately dependency-light so the individual test
scripts stay readable: image loading (with EXIF orientation applied),
EAN-13 checksum validation, and the sample-set discovery logic.
"""
from __future__ import annotations

import os
import re
import glob
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

# Repo root is two levels up from backend/tests/
REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DIRS = ["samples1", "samples2"]
RESULTS_DIR = Path(__file__).resolve().parent / "results"

# Only these formats are real retail product barcodes. Anything else
# (QR codes on hang tags, Data Matrix, etc.) must not be written into a
# product_id field -- see sample 25, which carries a QR code and no EAN.
RETAIL_FORMATS = {"EAN13", "EAN8", "UPCA", "UPCE"}

# The resolution the benchmark showed to be optimal.
DEFAULT_MAX_DIM = 1600


def natural_key(path: str):
    """Sort 'sample 2.jpg' before 'sample 10.jpg'."""
    base = os.path.basename(path)
    m = re.search(r"(\d+)", base)
    return (os.path.dirname(path), int(m.group(1)) if m else 0, base)


def sample_files(dirs=None):
    """All sample JPEGs across the sample folders, in natural order."""
    dirs = dirs or SAMPLE_DIRS
    out = []
    for d in dirs:
        out.extend(sorted(glob.glob(str(REPO_ROOT / d / "*.jpg")), key=natural_key))
    if not out:
        raise SystemExit(
            f"No sample images found under {REPO_ROOT}. "
            f"Expected folders: {', '.join(dirs)}"
        )
    return out


def load_gray(path: str, max_dim: int | None = DEFAULT_MAX_DIM) -> np.ndarray:
    """Load as grayscale with EXIF rotation applied, optionally downscaled.

    Applying exif_transpose is not optional: phone photos carry an
    orientation tag, and skipping it makes every downstream step read the
    image sideways.
    """
    im = ImageOps.exif_transpose(Image.open(path)).convert("L")
    if max_dim:
        im.thumbnail((max_dim, max_dim))
    return np.array(im)


def load_rgb(path: str, max_dim: int | None = DEFAULT_MAX_DIM) -> Image.Image:
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    if max_dim:
        im.thumbnail((max_dim, max_dim))
    return im


def ean13_valid(code: str) -> bool:
    """EAN-13 check-digit validation.

    NOTE: this is a 1-in-10 filter, not proof. The benchmark found an
    OCR misread that passed this check (8904505198366 for a pack whose
    true code is 8904505983665). Always cross-check a recovered code
    against the product master before trusting it.
    """
    if len(code) != 13 or not code.isdigit():
        return False
    d = [int(c) for c in code]
    return (sum(d[0:12:2]) + 3 * sum(d[1:12:2]) + d[12]) % 10 == 0


def repair_ean13(digits: str) -> list[str]:
    """Recover a full EAN-13 from a partial OCR read of the printed digits.

    OCR often drops the leading digit, which sits outside the guard bar.
    Brute-forcing the missing digit against the check digit usually leaves
    exactly one valid candidate.
    """
    digits = re.sub(r"\D", "", digits)
    if len(digits) == 13:
        return [digits] if ean13_valid(digits) else []
    if len(digits) == 12:
        return [p + digits for p in "0123456789" if ean13_valid(p + digits)]
    # Slide a 13-wide window over a longer noisy string.
    return [
        digits[i:i + 13]
        for i in range(len(digits) - 12)
        if ean13_valid(digits[i:i + 13])
    ]


def pick_retail(results):
    """First result that is an actual retail barcode format, else None."""
    for b in results:
        if b.format.name in RETAIL_FORMATS:
            return b
    return None


def rel_name(path: str) -> str:
    """'samples2/sample 42.jpg' -- stable label for reports."""
    p = Path(path)
    return f"{p.parent.name}/{p.name}"


def ensure_results_dir() -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return RESULTS_DIR
