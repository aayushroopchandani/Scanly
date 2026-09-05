"""The deterministic expiry parser.

    from app.expiry import parse
    result = parse(ocr_lines)

Implements the flow in section 4 of the pattern specification: resolve
indirection and open-shelf-life first, then a labelled value, then a
range, then derivation, and only then fall back to bare unlabelled dates.
The order matters -- it keeps decoys (import dates, batch codes) and
'see below' panels from being mistaken for a real value.

No machine learning, no network calls: the same text always produces the
same answer, and every answer names the pattern that produced it.
"""
from __future__ import annotations

from datetime import date

from . import strategies, validate
from .extract import scan_lines
from .types import Confidence, ExpiryResult, Pattern


def parse(lines: list[str], today: date | None = None) -> ExpiryResult:
    """Extract an expiry date from raw OCR text lines."""
    if not lines:
        return ExpiryResult(pattern=Pattern.E11_MISSING,
                            reason="no OCR text")

    scan = scan_lines(lines)

    result: ExpiryResult | None = None
    for strategy in strategies.ORDERED:
        result = strategy(scan)
        if result is not None:
            break
    if result is None:
        result = strategies.unresolved(scan)

    result.candidates = [
        f"{t.raw} -> {t.resolve()} [{t.fmt}/{t.role.value}]"
        for t in scan.dates
    ]

    if result.expiry is not None:
        usable, warnings = validate.check(result.expiry, result.manufacture,
                                          today)
        result.warnings = warnings
        if not usable:
            # The value failed a hard sanity rule -- report why, keep no date.
            return ExpiryResult(
                manufacture=result.manufacture, pattern=result.pattern,
                confidence=Confidence.NONE, needs_review=True,
                reason=f"rejected: {warnings[0] if warnings else 'failed sanity check'}",
                candidates=result.candidates)
        if warnings and result.confidence is Confidence.HIGH:
            result.confidence = Confidence.MEDIUM

    # Only a directly-labelled, cleanly-parsed date may skip confirmation,
    # and even then only once the pilot proves accuracy (spec section 4).
    result.needs_review = result.confidence is not Confidence.HIGH
    return result
