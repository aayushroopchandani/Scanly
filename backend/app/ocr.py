"""Text extraction with RapidOCR (PP-OCR models on onnxruntime).

Raw text only -- no date parsing, no normalisation. Turning these lines
into an expiry date is a separate concern; see
backend/tests/ocr_expiry/Expiry_Date_Pattern_Spec.pdf for the taxonomy
that step will be built against.
"""
from __future__ import annotations

import threading
import time

import numpy as np

_engine = None
_lock = threading.Lock()


def get_engine():
    """Process-wide RapidOCR singleton.

    Constructing RapidOCR loads the ONNX detection and recognition models
    from disk, which costs roughly a second. Doing that per request would
    dwarf every other cost in the pipeline, so it happens exactly once.
    """
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:                     # double-checked
                from rapidocr_onnxruntime import RapidOCR
                _engine = RapidOCR()
    return _engine


def is_loaded() -> bool:
    """Whether the ONNX models are already resident in this process."""
    return _engine is not None


def warmup() -> float:
    """Load the models ahead of the first real request. Returns seconds."""
    started = time.perf_counter()
    engine = get_engine()
    engine(np.full((64, 64, 3), 255, dtype=np.uint8))
    return round(time.perf_counter() - started, 2)


def extract(rgb: np.ndarray) -> dict:
    """Return every text line RapidOCR reads, in detection order."""
    started = time.perf_counter()
    try:
        result, _elapsed = get_engine()(rgb)
    except Exception as exc:                        # pragma: no cover
        return {"ok": False, "line_count": 0, "lines": [], "error": str(exc),
                "ms": round((time.perf_counter() - started) * 1000, 1)}

    lines = [text for _box, text, _conf in (result or [])]
    return {
        "ok": bool(lines),
        "line_count": len(lines),
        "lines": lines,
        "ms": round((time.perf_counter() - started) * 1000, 1),
    }
