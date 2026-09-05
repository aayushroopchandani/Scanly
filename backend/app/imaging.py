"""Load an image once, derive the two inputs the extractors need.

The barcode decoder and the OCR engine want different things, so we open
and orient the file a single time and produce two cheap derivations from
that one decode.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

from .config import (BARCODE_MAX_DIM, OCR_MAX_DIM, UNSHARP_AMOUNT,
                     UNSHARP_SIGMA, UNSHARP_WEIGHT)


@dataclass(frozen=True)
class Source:
    """One decoded, correctly-oriented photograph."""
    image: Image.Image      # RGB, EXIF-corrected, full resolution
    width: int
    height: int
    path: Path


def load(image_path: str | Path) -> Source:
    """Open, apply EXIF orientation, return the full-resolution RGB source.

    exif_transpose is not optional. Phone photos carry an orientation tag;
    skip it and every downstream step reads the image sideways.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"No such image: {path}")
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    return Source(image=im, width=im.width, height=im.height, path=path)


def _fit(im: Image.Image, max_dim: int) -> tuple[Image.Image, float]:
    """Downscale so the longest side is max_dim. Returns (image, scale).

    `scale` converts a coordinate in the resized image back to the
    original photograph, which is what the caller needs to report box
    positions the frontend can use.
    """
    out = im.copy()
    out.thumbnail((max_dim, max_dim), Image.LANCZOS)
    scale = im.width / out.width if out.width else 1.0
    return out, scale


def for_barcode(src: Source) -> tuple[np.ndarray, float]:
    """Grayscale, longest side BARCODE_MAX_DIM. Returns (array, scale)."""
    small, scale = _fit(src.image, BARCODE_MAX_DIM)
    return np.array(small.convert("L")), scale


def for_ocr(src: Source) -> tuple[np.ndarray, float]:
    """RGB, longest side OCR_MAX_DIM, mild unsharp mask."""
    small, scale = _fit(src.image, OCR_MAX_DIM)
    arr = np.array(small)
    blurred = cv2.GaussianBlur(arr, (0, 0), UNSHARP_SIGMA)
    sharpened = cv2.addWeighted(arr, UNSHARP_AMOUNT, blurred, UNSHARP_WEIGHT, 0)
    return sharpened, scale
