"""Score the deterministic parser against the ground-truth expiry dates.

Reads cached OCR output (fixtures/ocr_lines.json) so this measures the
PARSER, not OCR variance. Run make_fixture.py first if it is missing.

Two numbers matter, and only the second judges the parser:

  * overall      -- correct / all ground-truthed images
  * of reachable -- correct / images where the date is actually PRESENT
                    in the OCR text at all

The parser cannot beat 'reachable'; anything the OCR never read is not
its failure. Run:  python test_parser.py [-v]
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
TESTS_ROOT = HERE.parent
BACKEND = TESTS_ROOT.parent
for p in (str(TESTS_ROOT), str(BACKEND), str(HERE.parent / "ocr_expiry")):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.expiry import parse                       # noqa: E402
from ground_truth import EXPIRY_GROUND_TRUTH       # noqa: E402
from metric import matches                         # noqa: E402

FIXTURE = HERE / "fixtures" / "ocr_lines.json"
# The sample photographs were taken in 2026; judge "past/future" from then.
TODAY = date(2026, 9, 1)


def truth_date(value: str) -> date:
    d, m, y = value.split("/")
    return date(2000 + int(y), int(m), int(d))


def main() -> int:
    verbose = "-v" in sys.argv
    if not FIXTURE.exists():
        print(f"missing {FIXTURE}\nRun: python make_fixture.py")
        return 2
    fixture = json.load(open(FIXTURE))

    rows, patterns = [], Counter()
    for name, lines in fixture.items():
        base = name.split("/")[-1]
        expected = EXPIRY_GROUND_TRUTH.get(base)
        if not expected:
            continue
        result = parse(lines, today=TODAY)
        want = truth_date(expected)
        got = result.expiry
        ok = got == want
        # Was the date even readable in the OCR text?
        reachable = matches(expected, lines)
        patterns[result.pattern.value if result.pattern else "none"] += 1
        rows.append(dict(name=name, want=want, got=got, ok=ok,
                         reachable=reachable, result=result))

    n = len(rows)
    reachable = [r for r in rows if r["reachable"]]
    correct = [r for r in rows if r["ok"]]
    correct_reachable = [r for r in reachable if r["ok"]]
    wrong = [r for r in rows if not r["ok"] and r["got"] is not None]

    print(f"\n=== deterministic parser, {n} ground-truthed images ===")
    print(f"correct overall        : {len(correct)}/{n}  "
          f"({100*len(correct)/n:.0f}%)")
    print(f"date present in OCR    : {len(reachable)}/{n}   <- the ceiling")
    print(f"correct of reachable   : {len(correct_reachable)}/{len(reachable)}  "
          f"({100*len(correct_reachable)/max(len(reachable),1):.0f}%)")
    print(f"WRONG date returned    : {len(wrong)}   <- the dangerous number")

    print("\npatterns used:")
    for pat, count in patterns.most_common():
        print(f"   {pat:<34} {count}")

    conf = Counter(r["result"].confidence.value for r in rows)
    print("\nconfidence:", dict(conf))

    if wrong:
        print("\n--- WRONG (returned a date that is not the truth) ---")
        for r in wrong:
            print(f"  {r['name']:<26} want {r['want']}  got {r['got']}  "
                  f"[{r['result'].pattern.value}]")
            print(f"      {r['result'].reason}")

    missed = [r for r in reachable if not r["ok"] and r["got"] is None]
    if missed:
        print("\n--- MISSED (date was in the text, parser found nothing) ---")
        for r in missed:
            print(f"  {r['name']:<26} want {r['want']}  "
                  f"[{r['result'].pattern.value}] {r['result'].reason}")

    if verbose:
        print("\n--- all rows ---")
        for r in rows:
            mark = "OK " if r["ok"] else ("--" if r["reachable"] else "  ")
            print(f"{mark} {r['name']:<26} want {r['want']}  got {r['got']}  "
                  f"{r['result'].pattern.value if r['result'].pattern else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
