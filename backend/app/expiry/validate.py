"""Sanity rules from spec section 4.

These produce WARNINGS, not rejections. An expired pack is a legitimate
finding in a warehouse backfill -- refusing to report it would hide
exactly the stock the project exists to find. Only physically impossible
values are rejected outright.
"""
from __future__ import annotations

from datetime import date

# A pack may sit in the warehouse long after expiry; only flag the absurd.
MAX_YEARS_PAST = 3
MAX_YEARS_FUTURE = 12
# Observed shelf lives span 12 months to 5 years (sample 2: Apr26 -> Apr31).
PLAUSIBLE_SHELF_MONTHS = (1, 84)


def _months_between(a: date, b: date) -> int:
    return (b.year - a.year) * 12 + (b.month - a.month)


def check(expiry: date | None, manufacture: date | None,
          today: date | None = None) -> tuple[bool, list[str]]:
    """Return (is_usable, warnings)."""
    today = today or date.today()
    warnings: list[str] = []
    if expiry is None:
        return False, warnings

    years_off = (expiry - today).days / 365.25
    if years_off < -MAX_YEARS_PAST:
        warnings.append(
            f"expiry {expiry} is more than {MAX_YEARS_PAST} years past")
    elif expiry < today:
        warnings.append(f"expiry {expiry} is already past")
    if years_off > MAX_YEARS_FUTURE:
        return False, [f"expiry {expiry} is implausibly far in the future"]

    if manufacture:
        if expiry <= manufacture:
            return False, [
                f"expiry {expiry} is not after manufacture {manufacture}"]
        gap = _months_between(manufacture, expiry)
        lo, hi = PLAUSIBLE_SHELF_MONTHS
        if not (lo <= gap <= hi):
            warnings.append(
                f"shelf life of {gap} months is outside the usual {lo}-{hi}")
    return True, warnings
