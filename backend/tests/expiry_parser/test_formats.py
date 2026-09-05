"""Unit tests for date value formats, repair, and day inference.

Fast, no fixtures, no OCR. These guard the fiddly parts -- especially the
OCR-repair pass, which in an earlier revision silently rewrote
'03-03-2027' as '03-03-20' + '27' and turned a 2027 expiry into 2020.
That class of bug is invisible in aggregate scores, so it gets an
explicit test.

    python test_formats.py
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.expiry import parse                       # noqa: E402
from app.expiry.formats import find_dates          # noqa: E402
from app.expiry.normalise import repair            # noqa: E402

FAILURES: list[str] = []


def check(label: str, got, want) -> None:
    if got != want:
        FAILURES.append(f"{label}\n     got  {got!r}\n     want {want!r}")


def first_date(text: str):
    tokens = find_dates(text)
    return tokens[0].resolve() if tokens else None


def test_value_formats() -> None:
    """One case per V-id from the pattern specification."""
    cases = [
        ("V1 DD/MM/YYYY",        "EXP DATE:20/11/2026", date(2026, 11, 20)),
        ("V1 dashes",            "Bestbefore:03-03-2027", date(2027, 3, 3)),
        ("V2 DD/MM/YY",          "EXP22/05/27", date(2027, 5, 22)),
        ("V3 MM/YYYY",           "Best Before : 10/2027", date(2027, 10, 31)),
        ("V4 Month YYYY",        "Best Before: April 2031", date(2031, 4, 30)),
        ("V4 no separator",      "BestBefore:January2027", date(2027, 1, 31)),
        ("V5 MMM-YYYY",          "Expiry Date : FEB-2029", date(2029, 2, 28)),
        ("V6 DD Month YYYY",     "04 September 2027", date(2027, 9, 4)),
        ("V7 YYYYMMDD",          "EXP20260518", date(2026, 5, 18)),
        ("V8 YYYY.MMM.DD",       "EXP2028.JAN.21", date(2028, 1, 21)),
    ]
    for label, text, want in cases:
        check(label, first_date(text), want)


def test_day_inference() -> None:
    """Month-only values become the LAST day of that month."""
    check("Apr 2031 -> 30th", first_date("Best Before: April 2031"),
          date(2031, 4, 30))
    check("Oct 2028 -> 31st", first_date("Best Before: 10/2028"),
          date(2028, 10, 31))
    # 2028 is a leap year; a hard-coded 28 would be wrong here.
    check("Feb 2028 -> 29th (leap)", first_date("Expiry Date : FEB-2028"),
          date(2028, 2, 29))
    check("Feb 2027 -> 28th", first_date("Expiry Date : FEB-2027"),
          date(2027, 2, 28))


def test_repair_is_safe() -> None:
    """The repair pass must never corrupt an already-valid date.

    Regression: a two-digit-year rule with no look-ahead constraint split
    '03-03-2027' into '03-03-20' and '27'.
    """
    check("intact 4-digit year", repair("03-03-2027"), "03-03-2027")
    check("intact range", repair("09/2025-08/2028"), "09/2025-08/2028")
    check("date fused to time", repair("13/08/202713:47"),
          "13/08/2027 13:47")
    check("date fused to code", repair("13/02/202660444832GB"),
          "13/02/2026 60444832GB")
    check("two fused dates", repair("15/06/2614/06/27"),
          "15/06/26 14/06/27")
    check("repair is idempotent", repair(repair("15/06/2614/06/27")),
          "15/06/26 14/06/27")
    check("2027 stays 2027", first_date("Bestbefore:03-03-2027"),
          date(2027, 3, 3))


def test_decoys_are_rejected() -> None:
    """Import dates and batch codes must never be returned as an expiry."""
    result = parse(["Import Date : APR-2026", "Expiry Date : FEB-2029"],
                   today=date(2026, 9, 1))
    check("import date not chosen", result.expiry, date(2029, 2, 28))

    result = parse(["BARTCHNO:2501003", "MFD.DATE:20250110",
                    "JMPORTDATE:20250219"], today=date(2026, 9, 1))
    check("no expiry invented from decoys", result.expiry, None)


def test_shelf_life_derivation() -> None:
    result = parse(["MFG DATE 30/07/26", "Best Before 1 Year from Mfg. Dt."],
                   today=date(2026, 9, 1))
    check("mfg + 12 months", result.expiry, date(2027, 7, 30))
    check("shelf life recorded", result.shelf_life_months, 12)


def test_range_takes_later_half() -> None:
    result = parse(["252500902", "11/2025-10/2028"], today=date(2026, 9, 1))
    check("range -> later half", result.expiry, date(2028, 10, 31))


def test_confidence_and_review() -> None:
    labelled = parse(["EXP DATE:20/11/2026"], today=date(2026, 9, 1))
    check("labelled is high", labelled.confidence.value, "high")
    check("labelled skips review", labelled.needs_review, False)

    derived = parse(["MFG DATE 30/07/26", "Best Before 1 Year from Mfg. Dt."],
                    today=date(2026, 9, 1))
    check("derived is medium", derived.confidence.value, "medium")
    check("derived needs review", derived.needs_review, True)

    empty = parse([], today=date(2026, 9, 1))
    check("empty gives nothing", empty.expiry, None)
    check("empty needs review", empty.needs_review, True)


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn()
    total = len(tests)
    if FAILURES:
        print(f"FAILED  ({len(FAILURES)} check(s) across {total} tests)\n")
        for f in FAILURES:
            print(f"  ✗ {f}")
        return 1
    print(f"All {total} format/behaviour tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
