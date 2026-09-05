"""Date VALUE formats V1-V9 from the pattern specification.

Each matcher yields DateTokens with char offsets, so the caller can work
out which label a date belongs to. Order matters: ranges (V9) are matched
before the single formats so a range is not torn into two loose dates.
"""
from __future__ import annotations

import calendar
import re
from datetime import date

from .normalise import repair
from .types import DateToken

MIN_YEAR, MAX_YEAR = 2000, 2100

MONTHS = {m.upper(): i for i, m in enumerate(calendar.month_abbr) if m}
MONTHS.update({m.upper(): i for i, m in enumerate(calendar.month_name) if m})
# Common OCR damage on month names.
MONTHS.update({"0CT": 10, "SEPT": 9, "JANUARY": 1, "APRIL": 4})
_MONTH_ALT = "|".join(sorted(MONTHS, key=len, reverse=True))
_MONTH_NAMES = sorted(MONTHS, key=len, reverse=True)


def month_from_word(word: str) -> int | None:
    """Resolve a month name, tolerating a little OCR damage.

    Exact match first. Failing that, accept a name that appears inside the
    word -- 'SSEPTEMBER' -> September -- but only when the lengths are
    close, so 'MARKETED' can never be read as March.
    """
    word = word.upper().strip(".")
    if word in MONTHS:
        return MONTHS[word]
    for name in _MONTH_NAMES:
        if name in word and abs(len(word) - len(name)) <= 2:
            return MONTHS[name]
    return None

SEP = r"[/\-.]"


def _year(value: str) -> int:
    """Two-digit years are 20YY; expiry dates are never last century."""
    n = int(value)
    return 2000 + n if n < 100 else n


def _valid(y: int, m: int, d: int | None) -> bool:
    if not (MIN_YEAR <= y <= MAX_YEAR) or not (1 <= m <= 12):
        return False
    if d is None:
        return True
    return 1 <= d <= calendar.monthrange(y, m)[1]


# --- individual format patterns ---------------------------------------
# V9 first: a range must not be split into two independent dates.
V9_RANGE = re.compile(
    rf"(?<!\d)(\d{{1,2}}){SEP}(\d{{4}})\s*-\s*(\d{{1,2}}){SEP}(\d{{4}})(?!\d)")
# V9 with the separators eaten by OCR: 1112025-1012028 (sample 26)
V9_RANGE_DAMAGED = re.compile(r"(?<!\d)(\d{2})(\d{4})\s*-\s*(\d{2})(\d{4})(?!\d)")

V8_YMD_NAME = re.compile(rf"(?<!\d)(\d{{4}})\.({_MONTH_ALT})\.(\d{{1,2}})(?!\d)")
V7_YYYYMMDD = re.compile(r"(?<!\d)(\d{4})(\d{2})(\d{2})(?!\d)")
V6_DD_MONTH_Y = re.compile(r"(?<!\d)(\d{1,2})\s+([A-Z]{3,12})\.?\s+(\d{4})(?!\d)")
V1_DMY = re.compile(rf"(?<!\d)(\d{{1,2}}){SEP}(\d{{1,2}}){SEP}(\d{{2,4}})(?!\d)")
# V1 with one separator lost: 20-112026 (sample 1)
V1_DMY_DAMAGED = re.compile(rf"(?<!\d)(\d{{1,2}}){SEP}(\d{{2}})(\d{{4}})(?!\d)")
V5_MONTH_Y = re.compile(rf"(?<![A-Z0-9])([A-Z]{{3,12}})\.?\s*[-/ ]?\s*(\d{{4}})(?!\d)")
V3_MY = re.compile(rf"(?<!\d)(\d{{1,2}}){SEP}(\d{{4}})(?!\d)")


def _tok(raw, y, m, d, fmt, li, s, e, range_pos=None) -> DateToken | None:
    if not _valid(y, m, d):
        return None
    return DateToken(raw=raw, year=y, month=m, day=d, fmt=fmt,
                     line_index=li, start=s, end=e, range_pos=range_pos)


def find_dates(line: str, line_index: int = 0) -> list[DateToken]:
    """Every date in one line, left to right, non-overlapping.

    Formats are tried most-specific first; once a span is consumed it is
    not re-matched, which is what stops '09/2025-08/2028' becoming two
    unrelated MM/YYYY values.
    """
    upper = repair(line).upper()
    taken: list[tuple[int, int]] = []
    out: list[DateToken] = []

    def free(s: int, e: int) -> bool:
        return all(e <= ts or s >= te for ts, te in taken)

    def add(tok: DateToken | None, s: int, e: int) -> None:
        if tok and free(s, e):
            taken.append((s, e))
            out.append(tok)

    # V9 ranges (both spellings) -- emit BOTH halves, tagged by position.
    for rx, damaged in ((V9_RANGE, False), (V9_RANGE_DAMAGED, True)):
        for m in rx.finditer(upper):
            a_m, a_y, b_m, b_y = m.groups()
            first = _tok(m.group(0), _year(a_y), int(a_m), None, "V9",
                         line_index, m.start(), m.end(), range_pos=0)
            second = _tok(m.group(0), _year(b_y), int(b_m), None, "V9",
                          line_index, m.start(), m.end(), range_pos=1)
            if first and second and free(m.start(), m.end()):
                taken.append((m.start(), m.end()))
                out.extend([first, second])

    for m in V8_YMD_NAME.finditer(upper):
        y, mon, d = m.groups()
        add(_tok(m.group(0), _year(y), MONTHS.get(mon, 0), int(d), "V8",
                 line_index, m.start(), m.end()), m.start(), m.end())

    for m in V6_DD_MONTH_Y.finditer(upper):
        d, mon, y = m.groups()
        add(_tok(m.group(0), _year(y), month_from_word(mon) or 0, int(d), "V6",
                 line_index, m.start(), m.end()), m.start(), m.end())

    for m in V1_DMY.finditer(upper):
        d, mo, y = m.groups()
        fmt = "V2" if len(y) == 2 else "V1"
        tok = _tok(m.group(0), _year(y), int(mo), int(d), fmt,
                   line_index, m.start(), m.end())
        if tok is None:                      # maybe it was MM/DD/YYYY
            tok = _tok(m.group(0), _year(y), int(d), int(mo), fmt,
                       line_index, m.start(), m.end())
        add(tok, m.start(), m.end())

    for m in V1_DMY_DAMAGED.finditer(upper):
        d, mo, y = m.groups()
        add(_tok(m.group(0), _year(y), int(mo), int(d), "V1",
                 line_index, m.start(), m.end()), m.start(), m.end())

    for m in V7_YYYYMMDD.finditer(upper):
        y, mo, d = m.groups()
        add(_tok(m.group(0), int(y), int(mo), int(d), "V7",
                 line_index, m.start(), m.end()), m.start(), m.end())

    for m in V5_MONTH_Y.finditer(upper):
        mon, y = m.groups()
        add(_tok(m.group(0), _year(y), month_from_word(mon) or 0, None, "V4",
                 line_index, m.start(), m.end()), m.start(), m.end())

    for m in V3_MY.finditer(upper):
        mo, y = m.groups()
        add(_tok(m.group(0), _year(y), int(mo), None, "V3",
                 line_index, m.start(), m.end()), m.start(), m.end())

    out.sort(key=lambda t: (t.start, t.range_pos or 0))
    return out
