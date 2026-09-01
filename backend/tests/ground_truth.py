"""Ground truth for the sample set.

EXPIRY_GROUND_TRUTH is transcribed from
`samples2/Expiry mapping to sample photo.docx` (supplied with the photos).

BARCODE_CLASS is the result of manually inspecting every image that no
decoder could read, to separate "the decoder failed" from "there was
nothing to decode". Without this split the headline accuracy number is
meaningless: 22 of the 58 photos contain no product barcode at all.
"""

# --- expiry dates, DD/MM/YY -------------------------------------------------
# None = no expiry derivable from that single photo.
EXPIRY_GROUND_TRUTH = {
    "sample 1.jpg": "20/11/26",
    "sample 2.jpg": "30/04/31",
    "sample 3.jpg": "30/04/31",
    "sample 4.jpg": "30/04/27",
    "sample 5.jpg": "12/09/26",
    "sample 6.jpg": "30/04/31",
    "sample 7.jpg": "10/01/27",
    "sample 8.jpg": "17/02/27",
    "sample 9.jpg": "31/01/27",
    "sample 10.jpg": "03/03/27",
    "sample 11.jpg": "28/02/27",
    "sample 12.jpg": "28/02/27",
    "sample 13.jpg": "28/02/27",
    "sample 14.jpg": "28/02/27",
    "sample 15.jpg": "28/02/27",
    "sample 16.jpg": "11/09/26",
    "sample 17.jpg": "10/03/27",
    "sample 18.jpg": "23/07/27",
    "sample 19.jpg": "28/02/29",
    "sample 20.jpg": "13/11/27",
    "sample 21.jpg": "30/07/27",
    "sample 22.jpg": "28/07/27",
    "sample 23.jpg": "07/03/27",
    "sample 24.jpg": None,
    "sample 25.jpg": "31/10/27",
    "sample 26.jpg": "31/10/28",
    "sample 27.jpg": None,          # see sample 28
    "sample 28.jpg": "31/10/26",
    "sample 29.jpg": "31/08/28",
    "sample 30.jpg": "18/02/27",
    "sample 31.jpg": "15/12/27",
    "sample 32.jpg": None,
    "sample 33.jpg": "13/08/27",
    "sample 34.jpg": "04/09/27",
    "sample 35.jpg": "23/11/26",
    "sample 36.jpg": "14/06/27",
    "sample 37.jpg": "28/11/26",
    "sample 38.jpg": "22/05/27",
    "sample 39.jpg": "21/01/28",
    "sample 40.jpg": "30/04/31",
    "sample 41.jpg": "22/06/28",
    "sample 42.jpg": "18/05/26",
    "sample 43.jpg": "22/05/28",
    "sample 44.jpg": "29/02/28",
    "sample 45.jpg": "30/04/31",
    # 46 and 47 are the same product photographed from two sides.
    # Combined, the expiry is 04/08/27. Neither photo yields it alone.
    "sample 46.jpg": None,
    "sample 47.jpg": None,
    "sample 48.jpg": "23/07/27",
    "sample 49.jpg": "23/07/27",
}

# --- barcode presence classification ---------------------------------------
# Barcode is fully visible in frame but no decoder could read it.
# Both are curved jars; 192628 is also out of focus.
BARCODE_PRESENT_BUT_UNREAD = {
    "samples1/20260829_192628.jpg",
    "samples2/sample 47.jpg",
}

# Barcode is in frame but sliced by the edge of the photo -> undecodable.
# In every one of these the full EAN is also printed as plain text
# next to the expiry, so the OCR fallback can recover it.
BARCODE_CUT_OFF = {
    "samples2/sample 11.jpg",
    "samples2/sample 12.jpg",
    "samples2/sample 13.jpg",
    "samples2/sample 14.jpg",
    "samples2/sample 15.jpg",
}

# Photos containing no retail product barcode at all -- the employee
# photographed the expiry panel, and the barcode is on another face.
NO_BARCODE_IN_FRAME = {
    "samples2/sample %d.jpg" % n
    for n in (6, 17, 18, 19, 21, 22, 24, 25, 26, 27, 28, 29,
              32, 34, 35, 36, 41, 44, 45, 46, 48, 49)
}

# Known multi-barcode image: a shelf/multipack shot with six distinct,
# individually checksum-valid EAN-13s. Must not be auto-resolved.
MULTI_BARCODE = {"samples2/sample 42.jpg"}

# Carries a QR code (op691ab19bbf18b) and no retail barcode.
QR_ONLY = {"samples2/sample 25.jpg"}


def classify(rel_path: str) -> str:
    if rel_path in BARCODE_CUT_OFF:
        return "cut_off"
    if rel_path in NO_BARCODE_IN_FRAME:
        return "no_barcode"
    return "full_barcode"
