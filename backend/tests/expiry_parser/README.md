# Expiry-Parser Tests

Tests for [`backend/app/expiry/`](../../app/expiry/) — the deterministic,
rule-based parser that turns raw OCR text into a normalised expiry date.

```bash
python run_parser_tests.py
```

## Results

| Metric | Value |
|---|---|
| Correct overall | **32 / 44** (73%) |
| Date actually present in the OCR text | 30 / 44 ← the ceiling |
| **Correct of what is readable** | **30 / 30 (100%)** |
| **Wrong date returned** | **0** ← the number that matters most |

Overall *exceeds* the 30-image ceiling because sample 7's expiry is not in
the text at all — it is **derived** from `MFD 20250110` plus the pack's
"24 months from date of manufacture" statement.

The 12 images with no answer are genuinely unanswerable from one photo:
labels printed blank, "as printed on pack" indirection, a shelf life
relative to *opening*, or a manufacture date whose shelf life is not on
the panel (needs the per-SKU table).

### A wrong date is worse than no date

`0 wrong` is the headline. A silent misread writes a false expiry onto an
entire batch. Every heuristic result is capped at **medium** confidence
and flagged `needs_review`, so only cleanly-labelled dates (`high`) are
ever auto-save candidates.

| Confidence | Count | Meaning |
|---|---:|---|
| `high` | 22 | directly labelled, cleanly parsed |
| `medium` | 10 | derived or heuristic — must be confirmed |
| `none` | 12 | nothing usable — manual entry |

## Patterns exercised

| Pattern | Used | What it caught |
|---|---:|---|
| `E2_both_printed` | 13 | MFG and expiry both labelled |
| `E1_direct_labelled` | 10 | a plain labelled expiry |
| `E7_two_unlabelled_dates` | 6 | weighing stickers, bare date pairs |
| `E5_compressed_range` | 2 | `11/2025-10/2028` |
| `E4_mfg_only` | 2 | needs the per-SKU shelf-life table |
| `E3_derived` | 1 | MFG + "24 months from manufacture" |
| `E11_missing` | 10 | nothing readable |

## Files

| File | Purpose |
|---|---|
| `test_formats.py` | Unit tests: V1–V9, day inference, OCR repair, decoy rejection |
| `test_parser.py` | Scores the parser against `ground_truth.py` |
| `make_fixture.py` | Regenerates the cached OCR output |
| `fixtures/ocr_lines.json` | Cached OCR text for all 58 images |

## Why a fixture

`test_parser.py` reads cached OCR output rather than re-running RapidOCR.
That makes the suite fast and deterministic, and — more importantly — it
measures the **parser** rather than OCR variance. Regenerate only when the
OCR settings change:

```bash
python make_fixture.py
```

## Regression worth knowing about

An early version of the OCR-repair pass split `03-03-2027` into
`03-03-20` + `27`, silently turning a 2027 expiry into **2020**. Aggregate
accuracy barely moved, so the bug was nearly invisible. `test_formats.py`
now asserts explicitly that repair never alters an already-valid date.
