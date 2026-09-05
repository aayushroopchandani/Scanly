"""Tunables for the capture pipeline.

Every number here was measured, not guessed -- see backend/tests/ and the
benchmark report. Do not change them casually.
"""
from __future__ import annotations

# --- barcode -----------------------------------------------------------
# 1600px decoded 29/58 vs 27/58 at native resolution, and 5x faster.
# Bigger is NOT better: downscaling suppresses print texture and glare
# that confuse the scanline reader.
BARCODE_MAX_DIM = 1600

# Only these are real retail product barcodes. A QR code on a hang tag
# (sample 25) must never end up in a product_id field.
RETAIL_FORMATS = frozenset({"EAN13", "EAN8", "UPCA", "UPCE"})

# --- OCR ---------------------------------------------------------------
# 1000px scored 31/44 vs 29 at 1600 and 24 at native.
OCR_MAX_DIM = 1000

# Mild unsharp mask: +2 images, none lost, no extra cost (33/44).
# This is the ONLY preprocessing that helped. Adaptive threshold cost
# 12 images and CLAHE cost 3 -- both are for Tesseract, not PP-OCR.
UNSHARP_AMOUNT = 1.6
UNSHARP_SIGMA = 2.0
UNSHARP_WEIGHT = -0.6

# --- API ---------------------------------------------------------------
# A phone photo is 3-4 MB. The frontend should downscale to 1600px before
# uploading (the backend resizes to that anyway), but the cap protects a
# worker from a malformed or hostile upload.
MAX_UPLOAD_BYTES = 15 * 1024 * 1024

# Dev default. Lock this down to the PWA origin before any real deployment.
CORS_ORIGINS = ["*"]
