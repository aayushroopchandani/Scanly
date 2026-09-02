# Barcode & Expiry Capture — Benchmark Suite

Component-selection benchmarks for the expiry-date capture system, run
against the 58 real product photographs in `samples1/` and `samples2/`.

**Report:** [`results/Barcode_OCR_Benchmark_Report.pdf`](results/Barcode_OCR_Benchmark_Report.pdf)

## Conclusions

| Question | Answer | Evidence |
|---|---|---|
| Which barcode library? | **zxing-cpp** | 29/31 vs 21/31 for `cv2.barcode` |
| What input resolution? | **1600 px** | Best of six sizes; native is worse *and* 5x slower |
| Add a detector model to crop the barcode first? | **No** | Cropping decoded 28/58 vs 29/58 for plain resize |
| Can it tell when there is no barcode? | **Yes** | 0 false positives across 22 no-barcode images |
| Is OCR a safe fallback for the printed digits? | **Only with a catalogue lookup** | 5/29 recovered, 1 of them wrong |

### Expiry-date OCR ([full suite](ocr_expiry/README.md))

| Question | Answer | Evidence |
|---|---|---|
| Which OCR engine? | **RapidOCR** (PP-OCR, ONNX) | 31/44 raw, CPU-only, ~0.4s/image |
| What input resolution? | **1000 px** | beats 1600 / 2200 / 3000 / native |
| Preprocess the image? | **Only mild sharpening** | unsharp +2; adaptive threshold **−12** |
| Crop to the expiry region first? | **No** | hand-drawn perfect crops score 25/44 vs 31/44 |

The headline "50% decode rate" is misleading and should not be quoted alone:
**22 of the 58 photos contain no product barcode at all** (the employee
photographed the expiry panel; the barcode is on another face), and 5 more
have one sliced by the frame edge. On images that actually contain a fully
framed barcode, zxing-cpp reads 94%.

## Setup

```bash
cd backend/tests
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
python run_all.py          # barcode tests + the expiry-OCR suite
python run_all.py 01 02    # only the selected barcode tests
python run_all.py ocr      # only the expiry-OCR suite
python make_report.py      # regenerate the PDF from results/*.json
```

Individual tests run standalone too: `python test_01_decoder_comparison.py`.
The barcode tests take seconds; the OCR suite takes ~15 minutes on CPU.

## Files

| File | Purpose |
|---|---|
| `common.py` | Image loading (EXIF-aware), EAN-13 checksum + repair, sample discovery |
| `ground_truth.py` | Expiry ground truth, and the manual barcode-presence classification |
| `test_01_decoder_comparison.py` | zxing-cpp vs cv2.barcode, head to head |
| `test_02_resolution_and_crop.py` | Resolution sweep; does detect-then-crop help? |
| `test_03_failure_recovery.py` | Native / tiled / upscaled retries on every failure |
| `test_04_ocr_barcode_fallback.py` | OCR the printed digits + checksum validation |
| `ocr_expiry/` | **Expiry-date OCR suite** — see its own [README](ocr_expiry/README.md) |
| `make_report.py` | Builds the PDF report from `results/*.json` |
| `run_all.py` | Runs the suite, tees output to `results/` |

`ground_truth.py` holds the manual classification of which images actually
contain a barcode. Without that split the accuracy numbers are meaningless,
so keep it updated if new samples are added.

## Gotchas these tests encode

- **Always `exif_transpose()` first.** Phone photos carry an orientation tag;
  skip it and everything downstream reads sideways.
- **Filter to retail formats** (`EAN13/EAN8/UPCA/UPCE`). Sample 25 is a hang-tag
  QR code — without the filter its payload lands in a `product_id` field.
- **Handle multiple barcodes.** Sample 42 contains six valid EAN-13s (shelf
  shot), sample 38 has two. The two decoders returned *different* products for
  sample 42. Never silently take the first result.
- **A check digit is a 1-in-10 filter, not proof.** Test 4 found an OCR misread
  (`8904505198366`) that passes EAN-13 validation while the true code is
  `8904505983665`. Always confirm against the product master.
- **Some packs cannot be captured in one photo.** Samples 46 and 47 are the same
  product; the supplied ground truth notes the expiry is only derivable by
  combining both images.
