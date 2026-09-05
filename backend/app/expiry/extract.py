"""Scan OCR lines: find dates, find labels, and decide what each date means.

The core trick is positional. A single line often carries two labelled
dates -- 'MFG28/11/25;EXP22/05/27' or 'Import Date : APR-2026  Expiry
Date : FEB-2029' -- so a date takes the role of the NEAREST LABEL TO ITS
LEFT on the same line. When a line holds a label but no value, the label
carries forward to the next line, which is how 'Best Before:' followed by
'18/06/2025' on the next line resolves.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace

from .formats import find_dates
from .types import DateToken, Role
from .vocabulary import (DECOY_RE, EXPIRY_RE, INDIRECTION_RE, MANUFACTURE_RE,
                         OPENING_LIFE, SHELF_LIFE_PATTERNS)


# How many following lines a dangling label may claim.
CARRY_LINES = 3


@dataclass(frozen=True)
class Scan:
    """Everything the strategies need, extracted once."""
    dates: list[DateToken]
    has_indirection: bool
    shelf_life_months: int | None
    opening_life_months: int | None
    saw_expiry_label: bool
    saw_manufacture_label: bool


def _squash(text: str) -> tuple[str, list[int]]:
    """Uppercase, drop non-alphanumerics, keep a map back to original offsets.

    Labels are matched on this form so OCR damage that eats spaces and
    punctuation ('BestBefore', 'MFD(Date)', 'Month & Year of Import')
    still matches a single vocabulary entry.
    """
    out, index = [], []
    for i, ch in enumerate(text.upper()):
        if ch.isalnum():
            out.append(ch)
            index.append(i)
    return "".join(out), index


def _labels_in(line: str) -> list[tuple[int, Role]]:
    """(original char offset, role) for every label word found in a line."""
    squashed, index = _squash(line)
    found: list[tuple[int, Role]] = []
    for rx, role in ((EXPIRY_RE, Role.EXPIRY),
                     (MANUFACTURE_RE, Role.MANUFACTURE),
                     (DECOY_RE, Role.DECOY)):
        for m in rx.finditer(squashed):
            if m.start() >= len(index):
                continue
            # Reject a match that is merely the start of a longer word --
            # 'EXP' inside 'EXPORTER'. The test has to run on the ORIGINAL
            # text, not the squashed form: squashing deletes the '.' in
            # 'EXP.FEB 2027', which would otherwise look like one word.
            # A following digit is fine ('EXP2028.JAN.21'); only a letter
            # directly adjacent means we are inside a word.
            end_orig = index[m.end() - 1] + 1
            if end_orig < len(line) and line[end_orig].isalpha():
                continue
            found.append((index[m.start()], role))
    found.sort()
    # Keep the most specific role when two labels start at the same place.
    deduped: list[tuple[int, Role]] = []
    for pos, role in found:
        if deduped and deduped[-1][0] == pos:
            continue
        deduped.append((pos, role))
    return deduped


def _assign_roles(line: str, tokens: list[DateToken],
                  carried: Role) -> tuple[list[DateToken], Role]:
    """Give each date the role of the nearest label to its left.

    Returns the tokens plus the role to carry into the next line (set when
    a label appeared with no value after it).
    """
    labels = _labels_in(line)
    out: list[DateToken] = []
    for tok in tokens:
        role = carried
        for pos, lab_role in labels:
            if pos <= tok.start:
                role = lab_role
            else:
                break
        out.append(replace(tok, role=role))

    # What role, if any, carries into the following line?
    #
    # A trailing label with no value after it obviously carries. Less
    # obviously, a label must ALSO survive a line that consumed it, because
    # column layouts get flattened by OCR into a label followed by several
    # bare dates ('Use Before:' / '07/03/2025' / '07/03/2027', sample 23).
    # Only a new label displaces it.
    if labels:
        last_pos, last_role = labels[-1]
        dangling = not any(t.start >= last_pos for t in tokens)
        # Decoy labels never carry. A stray 'Batch No.' or 'Import Date:'
        # with nothing after it would otherwise poison the real dates on
        # the following lines (sample 36).
        carry = last_role if dangling and last_role is not Role.DECOY \
            else Role.UNKNOWN
    else:
        carry = carried            # no label here: keep whatever we had
    return out, carry


def _shelf_life_months(squashed_lines: list[str]) -> int | None:
    for line in squashed_lines:
        for rx, unit in SHELF_LIFE_PATTERNS:
            m = rx.search(line)
            if m:
                n = int(m.group(1))
                return n * 12 if unit == "years" else n
    return None


def _opening_life_months(squashed_lines: list[str]) -> int | None:
    for line in squashed_lines:
        m = OPENING_LIFE.search(line)
        if m:
            n = int(m.group(1))
            return n * 12 if m.group(2) == "YEAR" else n
    return None


def scan_lines(lines: list[str]) -> Scan:
    """Run the whole extraction pass over one image's OCR output."""
    squashed = [_squash(ln)[0] for ln in lines]
    dates: list[DateToken] = []
    carried = Role.UNKNOWN
    carry_budget = 0

    for i, line in enumerate(lines):
        tokens = find_dates(line, i)
        if carry_budget <= 0:
            carried = Role.UNKNOWN
        assigned, next_carry = _assign_roles(line, tokens, carried)
        dates.extend(assigned)
        # A carried label expires after a few lines so it cannot bleed
        # across the whole panel and mislabel unrelated dates.
        carry_budget = CARRY_LINES if next_carry is not carried else carry_budget - 1
        carried = next_carry

    return Scan(
        dates=dates,
        has_indirection=any(INDIRECTION_RE.search(s) for s in squashed),
        shelf_life_months=_shelf_life_months(squashed),
        opening_life_months=_opening_life_months(squashed),
        saw_expiry_label=any(EXPIRY_RE.search(s) for s in squashed),
        saw_manufacture_label=any(MANUFACTURE_RE.search(s) for s in squashed),
    )
