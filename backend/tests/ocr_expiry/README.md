# Expiry-Date OCR — Benchmark Suite

Component and pipeline decisions for reading the **expiry date** off a pack.
Scored against the 44 `samples2/` images that have a ground-truth date in
`../ground_truth.py`.

For the barcode side of the system, see [`../README.md`](../README.md).

## Conclusions

| Question | Answer | Evidence |
|---|---|---|
| Which OCR engine? | **RapidOCR** (PP-OCR models, ONNX) | 31/44 raw, CPU-only, ~0.4s/image |
| What input resolution? | **1000 px** | 1000 beats 1600/2200/3000/native |
| Preprocess the image? | **Only mild sharpening** | unsharp +2; threshold **−12** |
| Crop to the expiry region first? | **No** | perfect hand-drawn crops score 25/44 vs 31/44 |
| Do OCR models crop internally? | **Yes** | detection stage returns text polygons |

**Recommended pipeline** — 33/44 (75%), ~420 ms:

```
exif_transpose  →  resize to 1000px  →  unsharp mask  →  RapidOCR
```

## The counter-intuitive result

Every attempt to "help" the model by narrowing or cleaning its input **cost**
accuracy:

| intervention | effect |
|---|---|
| crop to OCR-detected text box, re-OCR | 31 → 31 (no change, 5× slower) |
| crop to hand-drawn date panel | 31 → **25** |
| adaptive threshold (binarise) | 31 → **19** |
| CLAHE contrast | 31 → **28** |
| unsharp mask | 31 → **33** ✓ |

The reason is distribution, not information. PP-OCR's detector (DBNet) and
recogniser are trained on **full natural photographs**. Cropping to ~24% of
the frame makes text occupy far more of the image than anything in training,
and detection degrades:

```
sample 1   whole image → 56 text boxes    cropped → 7 boxes (missed MFG/EXP entirely)
sample 4   whole image → 13 text boxes    cropped → 3 boxes of garbage
sample 48  whole → ":23/07/2027" ✓        cropped → "X : 23.0712027" ✗
```

Sample 1's crop contained the full `MFG DATE / EXP DATE` block with nothing
clipped — and still failed. So this is not a cropping-accuracy problem; a
better region-proposal model would not fix it.

This contradicts the original architecture proposal, which calls preprocessing
*"the biggest single lever on OCR accuracy"* and recommends crop + grayscale +
deskew + adaptive threshold. That advice is correct for **Tesseract**, which
needs binarised input. It is wrong for RapidOCR.

## Setup

Same dependencies as the parent suite:

```bash
pip install -r ../requirements.txt
```

## Running

```bash
python run_ocr_tests.py          # all four tests
python run_ocr_tests.py 01 03    # selected
python verify_boxes.py           # re-render the manual crops for eyeballing
```

Test 3 is the slow one (five OCR passes per image); the full suite takes
roughly 15 minutes on CPU.

## Files

| File | Purpose |
|---|---|
| `metric.py` | Scoring, shared setup, parent-path wiring |
| `date_panel_boxes.py` | Hand-drawn date-panel regions for all 44 images |
| `test_01_resolution_sweep.py` | What resolution to feed the engine |
| `test_02_preprocessing.py` | Seven preprocessing variants |
| `test_03_crop_strategies.py` | **Headline:** whole image vs three crop strategies |
| `test_04_rotation_and_parsing.py` | Rotation retry; raw OCR vs strict parser |
| `verify_boxes.py` | Renders the manual crops so they can be checked by eye |
| `run_ocr_tests.py` | Runs the suite, logs into `results/` |

## Measure the engine, not your regex

`metric.py` scores on whether the correct date appears **anywhere in the raw
OCR text, in any printed form** — no parsing, no normalisation. This matters:

```
correct date present in raw OCR text : 31/44
extracted by a strict DD/MM/YYYY regex : 22/44
```

An earlier version of this suite reported that lower figure and badly
understated the engine. Sample 39 returns `EXP2028.JAN.21` — exactly correct,
but it matches no conventional date pattern. Judge OCR with the parser out of
the loop.

## Gotchas encoded here

- **Four date formats** appear across the packs: `04/12/2026`, `20250110`
  (YYYYMMDD), `10/2027` (month-year), and `January 2027` (month name + year).
- **Some packs print no expiry at all** — only a manufacture date plus
  "Best Before 1 Year from Mfg. Dt." (samples 7, 21, 22). OCR reads the MFG
  date perfectly; the expiry must be derived per SKU. These are not OCR
  failures and should not be counted as such.
- **Sideways text needs a rotation retry.** Upright OCR returned
  `EPDATE210/2027`; rotated 90° it returned `EAPDATE23./10/2027`.
- **Boxes in `date_panel_boxes.py` were wrong on the first pass** for samples
  5, 9 and 14 (they caught the barcode instead). Always re-run
  `verify_boxes.py` after editing them.
