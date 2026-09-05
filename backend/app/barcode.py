"""Barcode decoding with zxing-cpp.

Returns EVERY barcode found, not just the first. Sample 42 in the sample
set carries six distinct, individually checksum-valid EAN-13 codes (a
shelf/multipack shot) and sample 38 carries two -- silently taking the
first would write the wrong product_id. Each result carries its position
so the employee can later be shown the boxes and pick the right one.
"""
from __future__ import annotations

import time

import numpy as np
import zxingcpp

from .config import RETAIL_FORMATS


def _corners(position) -> list[tuple[int, int]]:
    p = position
    return [(int(pt.x), int(pt.y)) for pt in
            (p.top_left, p.top_right, p.bottom_right, p.bottom_left)]


def _describe(bc, scale: float, img_w: int, img_h: int) -> dict:
    """One decoded barcode, with its box mapped back to original pixels."""
    corners = [(int(x * scale), int(y * scale)) for x, y in _corners(bc.position)]
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    fmt = bc.format.name
    return {
        "value": bc.text,
        "format": fmt,
        # Only retail formats may be used as a product_id. A QR code on a
        # hang tag decodes fine but identifies nothing (sample 25).
        "is_retail": fmt in RETAIL_FORMATS,
        # Axis-aligned box in ORIGINAL image pixels -- for cropping.
        "box": {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0},
        # Same box normalised 0-1 -- survives any display resize, which is
        # what a frontend overlay actually wants.
        "box_norm": {
            "x": round(x0 / img_w, 5), "y": round(y0 / img_h, 5),
            "w": round((x1 - x0) / img_w, 5), "h": round((y1 - y0) / img_h, 5),
        },
        # Exact quad, in case the code is rotated in frame.
        "corners": corners,
    }


def decode(gray: np.ndarray, scale: float, img_w: int, img_h: int) -> dict:
    """Decode every barcode in the image.

    An empty list is a trustworthy "no barcode here": across 22 sample
    photographs containing none, zxing-cpp produced zero false positives.
    """
    started = time.perf_counter()
    try:
        found = zxingcpp.read_barcodes(gray)
    except Exception as exc:                       # pragma: no cover
        return {"ok": False, "count": 0, "values": [], "error": str(exc),
                "ms": round((time.perf_counter() - started) * 1000, 1)}

    values = [_describe(b, scale, img_w, img_h) for b in found]
    # Retail codes first -- the caller almost always wants those.
    values.sort(key=lambda v: (not v["is_retail"], v["box"]["y"]))
    ms = round((time.perf_counter() - started) * 1000, 1)
    return {
        "ok": bool(values),
        "count": len(values),
        "retail_count": sum(1 for v in values if v["is_retail"]),
        "values": values,
        "ms": ms,
    }
