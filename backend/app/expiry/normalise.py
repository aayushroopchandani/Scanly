"""Step 1 of the parser flow: repair OCR damage before matching.

OCR reliably eats separators, which welds tokens together and hides
otherwise-valid dates:

    '13/08/202713:47'        a date fused to a time      (sample 33)
    '13/02/202660444832GB'   a date fused to a code      (sample 33)
    '15/06/2614/06/27'       two dates fused together    (sample 36)

Both rules below are deliberately narrow. An earlier, looser version
split '03-03-2027' into '03-03-20' + '27' because it allowed a two-digit
year to be followed by anything, which silently turned 2027 into 2020.
A repair pass must never be able to corrupt a value that was already
correct, so each rule now requires unambiguous evidence of fusion.
"""
from __future__ import annotations

import re

# A COMPLETE four-digit year followed by another digit. A real date is
# never followed immediately by a digit, so this is always fusion.
_FUSED_AFTER_FULL_YEAR = re.compile(
    r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4})(?=\d)")

# A two-digit year followed by what is unmistakably the start of another
# date ('15/06/26' + '14/06/27'). Requiring the next token to look like a
# date is what stops this rule from chopping a four-digit year in half.
_FUSED_TWO_DATES = re.compile(
    r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2})(?=\d{1,2}[/\-.]\d)")

# A time-of-day welded onto whatever precedes it.
_FUSED_TIME = re.compile(r"(?<=\d)(?=\d{2}:\d{2}\b)")


def repair(line: str) -> str:
    """Insert the separators OCR dropped. Idempotent."""
    out = _FUSED_TIME.sub(" ", line)
    for _ in range(3):        # a run of fused dates needs several passes
        new = _FUSED_TWO_DATES.sub(r"\1 ", _FUSED_AFTER_FULL_YEAR.sub(r"\1 ", out))
        if new == out:
            break
        out = new
    return out
