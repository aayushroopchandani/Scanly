"""Value objects for the deterministic expiry parser.

Naming follows the pattern specification (backend/tests/ocr_expiry/
Expiry_Date_Pattern_Spec.pdf): V-ids are date VALUE formats, E-ids are
structural EXTRACTION patterns.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class Role(str, Enum):
    """What a label says a date means."""
    EXPIRY = "expiry"
    MANUFACTURE = "manufacture"
    DECOY = "decoy"          # import date, packing date -- never the answer
    UNKNOWN = "unknown"      # a bare date with no label


class Pattern(str, Enum):
    """Extraction pattern actually used, per spec section 3."""
    E1_DIRECT = "E1_direct_labelled"
    E2_BOTH = "E2_both_printed"
    E3_DERIVED = "E3_derived_from_shelf_life"
    E4_NO_SHELF_LIFE = "E4_mfg_only_shelf_life_unknown"
    E5_RANGE = "E5_compressed_range"
    E6_STICKER = "E6_weighing_sticker"
    E7_TWO_DATES = "E7_two_unlabelled_dates"
    E8_COMBINED = "E8_combined_label"
    E9_INDIRECTION = "E9_indirection"
    E10_OPEN_LIFE = "E10_use_within_of_opening"
    E11_MISSING = "E11_missing_or_blank"


class Confidence(str, Enum):
    """Drives the capture workflow, per spec section 4.

    HIGH   -- directly labelled and cleanly parsed; auto-save candidate
    MEDIUM -- derived or heuristic; ALWAYS needs the employee to confirm
    NONE   -- nothing usable; manual entry
    """
    HIGH = "high"
    MEDIUM = "medium"
    NONE = "none"


@dataclass(frozen=True)
class DateToken:
    """One date found in the text, before we know what it means."""
    raw: str
    year: int
    month: int
    day: int | None          # None => month-year only, needs day inference
    fmt: str                 # "V1".."V9"
    line_index: int
    start: int               # char offset within its line
    end: int
    role: Role = Role.UNKNOWN
    range_pos: int | None = None   # 0 = first half, 1 = second half (V9)

    @property
    def is_month_only(self) -> bool:
        return self.day is None

    def resolve(self) -> date:
        """Concrete date. Month-only values become the LAST day of the month.

        Confirmed against ground truth: 'April 2031' -> 30/04/2031,
        '10/2028' -> 31/10/2028, and 'FEB-2028' -> 29/02/2028 because
        2028 is a leap year. calendar.monthrange handles that; a
        hard-coded 28/30/31 table would not.
        """
        day = self.day or calendar.monthrange(self.year, self.month)[1]
        return date(self.year, self.month, day)


@dataclass
class ExpiryResult:
    """What the parser concluded."""
    expiry: date | None = None
    manufacture: date | None = None
    pattern: Pattern | None = None
    confidence: Confidence = Confidence.NONE
    needs_review: bool = True
    reason: str = ""
    warnings: list[str] = field(default_factory=list)
    candidates: list[str] = field(default_factory=list)
    shelf_life_months: int | None = None

    def as_dict(self) -> dict:
        return {
            "expiry": self.expiry.isoformat() if self.expiry else None,
            "manufacture": (self.manufacture.isoformat()
                            if self.manufacture else None),
            "pattern": self.pattern.value if self.pattern else None,
            "confidence": self.confidence.value,
            "needs_review": self.needs_review,
            "reason": self.reason,
            "warnings": self.warnings,
            "shelf_life_months": self.shelf_life_months,
            "candidates": self.candidates,
        }
