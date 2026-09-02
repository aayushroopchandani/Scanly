"""Render the hand-drawn date-panel crops so they can be checked by eye.

Every box in date_panel_boxes.py was validated with this before being used
in test_03. Three boxes were wrong on the first pass (samples 5, 9 and 14
caught the barcode instead of the date block) -- worth re-running this if
the boxes are ever edited.

    python verify_boxes.py              # all boxes, 12 per sheet
    python verify_boxes.py 5 9 14       # only these samples
"""
from __future__ import annotations

import sys

from PIL import Image, ImageDraw, ImageOps

from date_panel_boxes import BOX
from metric import ensure_results_dir, image_path

CELL_W, CELL_H, COLS = 430, 230, 4


def main():
    wanted = [int(a) for a in sys.argv[1:]] or sorted(BOX)
    nums = [n for n in wanted if n in BOX]
    rows = (len(nums) + COLS - 1) // COLS
    sheet = Image.new("RGB", (CELL_W * COLS, rows * (CELL_H + 20)), "white")
    draw = ImageDraw.Draw(sheet)

    for i, n in enumerate(nums):
        im = ImageOps.exif_transpose(Image.open(image_path(n))).convert("RGB")
        W, H = im.size
        x0, y0, x1, y1 = BOX[n]
        crop = im.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)))
        crop.thumbnail((CELL_W, CELL_H))
        ox, oy = (i % COLS) * CELL_W, (i // COLS) * (CELL_H + 20)
        sheet.paste(crop, (ox, oy + 20))
        draw.text((ox + 4, oy + 5), f"sample {n}", fill="black")

    out = ensure_results_dir() / "date_panel_crops.jpg"
    sheet.save(out, quality=85)
    print(f"wrote {out}  ({len(nums)} crops)")
    print("Check every crop actually contains the batch / MFG / expiry block.")


if __name__ == "__main__":
    main()
