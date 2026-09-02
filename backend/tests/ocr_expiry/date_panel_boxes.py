"""Hand-drawn date-panel regions for every sample with a ground-truth expiry.

Each box is a NORMALISED (x0, y0, x1, y1) rectangle covering the whole
batch / MFG / expiry block on that pack -- deliberately loose, not a tight
box around the date itself. Every box was checked by eye against a rendered
crop before use.

These exist to answer one question: if a perfect region-proposal step handed
the OCR engine exactly the right panel, would accuracy improve?

It does not. See test_03_crop_strategies.py -- cropping to these panels
scores 25/44 against 31/44 for the untouched image.
"""

# Manually recorded date-panel regions (normalised x0,y0,x1,y1).
# Deliberately loose: each covers the whole batch/MFG/expiry block, not just the date.
BOX = {
 1:(0.08,0.76,0.58,0.97),  2:(0.42,0.50,0.84,0.72),  3:(0.10,0.46,0.45,0.68),
 4:(0.06,0.53,0.85,0.72),  5:(0.06,0.55,0.62,0.75),  6:(0.52,0.28,0.80,0.68),
 7:(0.50,0.57,0.95,0.75),  8:(0.55,0.65,0.95,0.82),  9:(0.20,0.44,0.82,0.66),
10:(0.36,0.57,0.85,0.74), 11:(0.10,0.50,0.68,0.78), 12:(0.45,0.55,0.85,0.80),
13:(0.32,0.44,0.85,0.62), 14:(0.15,0.38,0.70,0.68), 15:(0.10,0.70,0.90,0.95),
16:(0.33,0.50,1.00,0.80), 17:(0.20,0.40,0.75,0.62), 18:(0.20,0.38,0.75,0.62),
19:(0.12,0.42,0.92,0.62), 20:(0.20,0.44,0.92,0.62), 21:(0.05,0.44,0.85,0.68),
22:(0.35,0.46,0.98,0.70), 23:(0.14,0.56,0.72,0.80), 25:(0.24,0.30,0.82,0.50),
26:(0.32,0.30,0.78,0.50), 28:(0.26,0.20,0.82,0.46), 29:(0.28,0.44,0.72,0.64),
30:(0.42,0.42,0.88,0.60), 31:(0.42,0.54,0.90,0.72), 33:(0.20,0.44,0.80,0.64),
34:(0.20,0.56,0.92,0.74), 35:(0.20,0.30,0.88,0.56), 36:(0.20,0.46,0.80,0.70),
37:(0.22,0.44,0.88,0.66), 38:(0.16,0.66,0.72,0.85), 39:(0.28,0.56,0.68,0.74),
40:(0.16,0.44,0.70,0.66), 41:(0.34,0.16,0.98,0.50), 42:(0.08,0.38,0.80,0.60),
43:(0.20,0.56,0.92,0.75), 44:(0.10,0.54,0.72,0.78), 45:(0.28,0.38,0.82,0.64),
48:(0.16,0.40,0.72,0.62), 49:(0.28,0.40,0.82,0.62),
}

# Pad every box outward -- the region only needs to be "vague", and this
# absorbs the +/-0.05 error in reading coordinates off a contact sheet.
PAD = 0.06
BOX = {k: (max(0.0,x0-PAD), max(0.0,y0-PAD), min(1.0,x1+PAD), min(1.0,y1+PAD))
       for k,(x0,y0,x1,y1) in BOX.items()}
