"""Resolution strategies E1-E11, applied in the order given by spec 4.

Each strategy inspects the Scan and either returns an ExpiryResult or
None, meaning "not my case, try the next one". Keeping them separate and
ordered is what makes the parser auditable -- every answer records which
pattern produced it.
"""
from __future__ import annotations

from datetime import date

from dateutil.relativedelta import relativedelta

from .extract import Scan
from .types import Confidence, DateToken, ExpiryResult, Pattern, Role


def _latest(tokens: list[DateToken]) -> DateToken | None:
    return max(tokens, key=lambda t: t.resolve(), default=None)


def _by_role(scan: Scan, role: Role) -> list[DateToken]:
    return [t for t in scan.dates if t.role is role]


def _mfg(scan: Scan) -> date | None:
    tokens = _by_role(scan, Role.MANUFACTURE)
    return min((t.resolve() for t in tokens), default=None)


# --- E9 / E10: no date exists here, and we can say why -----------------
def indirection(scan: Scan) -> ExpiryResult | None:
    """'as printed on pack', 'SEE BELOW' -- the value is somewhere else."""
    if not scan.has_indirection:
        return None
    # 'SEE BELOW' often sits above the very panel it points at, which OCR
    # then reads anyway (sample 36). Only give up when nothing was found.
    usable = [t for t in scan.dates if t.role is not Role.DECOY]
    if usable:
        return None
    return ExpiryResult(
        pattern=Pattern.E9_INDIRECTION, confidence=Confidence.NONE,
        reason="pack points elsewhere for the date ('as printed on pack')",
        manufacture=_mfg(scan))


def opening_life(scan: Scan) -> ExpiryResult | None:
    """'use within 3 months of opening' -- no fixed expiry can exist."""
    if scan.opening_life_months is None:
        return None
    if any(t.role is Role.EXPIRY for t in scan.dates):
        return None
    return ExpiryResult(
        pattern=Pattern.E10_OPEN_LIFE, confidence=Confidence.NONE,
        reason=(f"shelf life is {scan.opening_life_months} months from opening, "
                "not a fixed date"),
        manufacture=_mfg(scan))


# --- E1 / E2: a labelled expiry value ----------------------------------
def labelled(scan: Scan) -> ExpiryResult | None:
    tokens = _by_role(scan, Role.EXPIRY)
    if not tokens:
        return None
    # Several expiry-labelled dates can appear when OCR duplicates a line;
    # the latest is the safe pick (a mis-associated MFG would be earlier).
    token = _latest(tokens)

    # Column layouts get flattened by OCR, which can strand the expiry
    # several lines away from its label while the manufacture date sits
    # right next to it (sample 23: 'Use Before:' / '07/03/2025' / ...
    # / '07/03/2027'). Two dates sharing a day and month but differing in
    # year are a manufacture/expiry pair, and the later one is the expiry
    # -- a pack never prints two expiry dates.
    siblings = [t for t in scan.dates
                if t.role in (Role.EXPIRY, Role.UNKNOWN)
                and t.day == token.day and t.month == token.month
                and t.resolve() > token.resolve()]
    if siblings:
        token = _latest(siblings)

    mfg = _mfg(scan)
    pattern = Pattern.E2_BOTH if mfg else Pattern.E1_DIRECT
    return ExpiryResult(
        expiry=token.resolve(), manufacture=mfg, pattern=pattern,
        confidence=Confidence.HIGH,
        reason=f"expiry label followed by {token.fmt} value {token.raw!r}")


# --- E5: compressed MFG-EXP range --------------------------------------
def compressed_range(scan: Scan) -> ExpiryResult | None:
    halves = [t for t in scan.dates if t.range_pos is not None]
    if not halves:
        return None
    second = [t for t in halves if t.range_pos == 1]
    first = [t for t in halves if t.range_pos == 0]
    if not second:
        return None
    token = _latest(second)
    return ExpiryResult(
        expiry=token.resolve(),
        manufacture=min((t.resolve() for t in first), default=None),
        pattern=Pattern.E5_RANGE, confidence=Confidence.MEDIUM,
        reason=f"MFG-EXP range {token.raw!r}; took the later half")


# --- E3: derive from a manufacture date plus a shelf-life phrase -------
def derived(scan: Scan) -> ExpiryResult | None:
    if scan.shelf_life_months is None:
        return None
    mfg = _mfg(scan)
    if mfg is None:
        # A bare date with a shelf-life phrase is almost certainly the MFG.
        loose = [t for t in scan.dates if t.role in (Role.UNKNOWN,)]
        mfg = min((t.resolve() for t in loose), default=None)
    if mfg is None:
        return None
    months = scan.shelf_life_months
    return ExpiryResult(
        expiry=mfg + relativedelta(months=months), manufacture=mfg,
        pattern=Pattern.E3_DERIVED, confidence=Confidence.MEDIUM,
        shelf_life_months=months,
        reason=f"derived: manufacture {mfg} + {months} months from label text")


# --- E6 / E7 / E8: unlabelled dates, later one wins ---------------------
def unlabelled(scan: Scan) -> ExpiryResult | None:
    """Weighing stickers and bare date pairs.

    Decoys (import date, batch numbers) are excluded by role. Of what
    remains, the latest date is the expiry because MFG always precedes it.
    """
    usable = [t for t in scan.dates if t.role in (Role.UNKNOWN,)]
    # The spec's E6/E7 are about picking the LATER of several dates. A
    # single bare date carries no such evidence: on sample 22 the only
    # date is the manufacture date, whose label OCR placed on the
    # following line, and answering with it would report a pack as
    # expiring on the day it was made.
    if len(usable) < 2:
        return None
    token = _latest(usable)
    others = [t.resolve() for t in usable if t is not token]
    mfg = min(others, default=None)
    pattern = Pattern.E6_STICKER if len(usable) >= 3 else Pattern.E7_TWO_DATES
    return ExpiryResult(
        expiry=token.resolve(), manufacture=mfg, pattern=pattern,
        confidence=Confidence.MEDIUM,
        reason=(f"{len(usable)} unlabelled dates; took the latest "
                f"({token.raw!r})"))


# --- E4 / E11: nothing usable ------------------------------------------
def unresolved(scan: Scan) -> ExpiryResult:
    mfg = _mfg(scan)
    if mfg is None and scan.saw_manufacture_label:
        # Label and value ended up on separate lines in the wrong order,
        # so the date never got its role. It is still a manufacture date.
        loose = [t for t in scan.dates if t.role is Role.UNKNOWN]
        mfg = min((t.resolve() for t in loose), default=None)
    if mfg is not None:
        return ExpiryResult(
            manufacture=mfg, pattern=Pattern.E4_NO_SHELF_LIFE,
            confidence=Confidence.NONE,
            reason=("manufacture date read but no shelf life on the pack; "
                    "needs the per-SKU shelf-life table"))
    return ExpiryResult(
        pattern=Pattern.E11_MISSING, confidence=Confidence.NONE,
        reason="no expiry date found in the text")


# Order is the spec's section-4 flow and must not be shuffled.
ORDERED = (indirection, opening_life, labelled, compressed_range,
           derived, unlabelled)
