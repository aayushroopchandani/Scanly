"""Generate the Expiry-Date Pattern Specification PDF.

A reference document for building the deterministic expiry-date parser. It
catalogues every date VALUE format, LABEL word, and structural EXTRACTION
pattern observed in the raw RapidOCR output across all 58 sample photographs
(samples1/ + samples2/), plus a per-image appendix.

This is documentation, not a benchmark -- the numbers here were read by hand
from the OCR output of test_04 / the classify pass. Regenerate with:

    python make_pattern_spec.py
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether,
                                PageBreak, PageTemplate, Paragraph, Spacer,
                                Table, TableStyle)

OUT = Path(__file__).resolve().parent / "Expiry_Date_Pattern_Spec.pdf"

INK = colors.HexColor("#1a1a1a")
MUTED = colors.HexColor("#5f6b7a")
RULE = colors.HexColor("#d4dae2")
BAND = colors.HexColor("#eef2f7")
GOOD = colors.HexColor("#1a7f4b")
BAD = colors.HexColor("#b3261e")
WARN = colors.HexColor("#8a5a00")
CODEBG = colors.HexColor("#f4f6f9")

ss = getSampleStyleSheet()
S = {
    "title": ParagraphStyle("title", parent=ss["Title"], fontName="Helvetica-Bold",
                            fontSize=21, leading=25, textColor=INK,
                            alignment=TA_LEFT, spaceAfter=2),
    "sub": ParagraphStyle("sub", parent=ss["Normal"], fontName="Helvetica",
                          fontSize=10.5, leading=15, textColor=MUTED, spaceAfter=13),
    "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontName="Helvetica-Bold",
                         fontSize=14, leading=18, textColor=INK,
                         spaceBefore=15, spaceAfter=7),
    "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold",
                         fontSize=11, leading=15, textColor=INK,
                         spaceBefore=10, spaceAfter=5),
    "body": ParagraphStyle("body", parent=ss["Normal"], fontName="Helvetica",
                           fontSize=9.6, leading=14.2, textColor=INK, spaceAfter=7),
    "small": ParagraphStyle("small", parent=ss["Normal"], fontName="Helvetica",
                            fontSize=8.3, leading=11.8, textColor=MUTED, spaceAfter=6),
    "bullet": ParagraphStyle("bullet", parent=ss["Normal"], fontName="Helvetica",
                             fontSize=9.6, leading=14, textColor=INK,
                             leftIndent=13, bulletIndent=3, spaceAfter=3),
    "code": ParagraphStyle("code", parent=ss["Normal"], fontName="Courier",
                           fontSize=8.6, leading=12.4, textColor=INK,
                           backColor=CODEBG, borderPadding=6, leftIndent=3,
                           spaceAfter=8),
}


def P(t, s="body"):
    return Paragraph(t, S[s])


def B(t):
    return Paragraph(t, S["bullet"], bulletText="•")


def callout(text, tone=WARN):
    t = Table([[Paragraph(text, S["body"])]], colWidths=[166 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fdf6e8")),
        ("LINEBEFORE", (0, 0), (0, -1), 2.4, tone),
        ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def table(data, widths, align_left_all=True, header=True, mono_cols=()):
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    style = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (-1, 0), INK),
        ("BACKGROUND", (0, 0), (-1, 0), BAND),
        ("LINEBELOW", (0, 0), (-1, 0), 0.9, RULE),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, colors.HexColor("#eaeef3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]
    for c in mono_cols:
        style.append(("FONTNAME", (c, 1), (c, -1), "Courier"))
        style.append(("FONTSIZE", (c, 1), (c, -1), 7.8))
    t.setStyle(TableStyle(style))
    return t


def section(*flowables):
    return KeepTogether(list(flowables))


story = []

# ============================================================ cover
story += [
    P("Expiry-Date Pattern Specification", "title"),
    P("Reference for the deterministic expiry-date parser &nbsp;·&nbsp; "
      "derived from raw RapidOCR output over 58 sample photographs &nbsp;·&nbsp; "
      f"{date.today():%d %B %Y}", "sub"),
]
story += [P(
    "This document catalogues what the expiry information on JustDogs stock actually "
    "looks like once RapidOCR has read it, so the parser can be built against real "
    "cases rather than assumptions. It has four parts: the <b>date value formats</b> "
    "(how a date is written), the <b>label vocabulary</b> (the words around it, and "
    "which mean expiry, manufacture, or a decoy), the <b>extraction patterns</b> "
    "(the structural cases the parser must resolve), and a <b>per-image appendix</b> "
    "tagging all 58 photographs.", "body")]
story += [callout(
    "<b>Scope &amp; honesty note.</b> These patterns were read by hand from the OCR "
    "output of every sample. They cover this dataset (9 + 49 images); they are not a "
    "closed set for all suppliers JustDogs will ever stock. Treat this as the "
    "starting taxonomy, and expect the per-SKU shelf-life table and a review queue to "
    "cover what the rules miss.", WARN)]

# ============================================================ 1. value formats
story += [P("1. Date value formats", "h1")]
story += [P(
    "Every way a single date is written on the packs. The parser needs a matcher for "
    "each, and a <b>day-inference rule</b> for the month-only formats (V3–V5, V9).",
    "body")]
story += [table([
    ["ID", "Format", "Example (as OCR'd)", "Seen on", "Notes for the matcher"],
    ["V1", "DD/MM/YYYY", "20/11/2026, 03-03-2027", "many", "'/', '-' or '.' separators"],
    ["V2", "DD/MM/YY", "22/05/27", "38, 48, 49", "2-digit year → assume 20YY"],
    ["V3", "MM/YYYY", "10/2027", "25", "day → last day of month"],
    ["V4", "Month YYYY", "April 2031, January 2027", "2,3,6,9,40,45", "full or 3-letter month"],
    ["V5", "MMM-YYYY", "FEB-2029, APR-2026", "19, 44", "hyphen; day → last of month"],
    ["V6", "DD Month YYYY", "04 September 2027", "34", "spelled-out day + month"],
    ["V7", "YYYYMMDD run", "20260518", "42, 7", "8 digits, no separators"],
    ["V8", "YYYY.MMM.DD", "2028.JAN.21", "39", "year-first, dotted"],
    ["V9", "MM/YYYY-MM/YYYY", "09/2025-08/2028", "26, 29", "range; expiry = 2nd half"],
], [10 * mm, 30 * mm, 44 * mm, 26 * mm, 56 * mm], mono_cols=(2,))]
story += [callout(
    "<b>Day-inference rule (critical).</b> When only month + year are printed (V3, V4, "
    "V5, and the second half of V9), the expiry day is the <b>last day of that month</b> "
    "— confirmed against ground truth: <font face='Courier'>April 2031 → "
    "30/04/31</font>, <font face='Courier'>10/2028 → 31/10/28</font>. Watch "
    "February: <font face='Courier'>FEB-2028 → 29/02/28</font> (2028 is a leap "
    "year). Use a real calendar function, never a hard-coded 28/30/31.", BAD)]

# ============================================================ 2. label vocabulary
story += [P("2. Label vocabulary", "h1")]
story += [P(
    "The words that appear next to a date decide what it means. Three buckets, plus "
    "the shelf-life phrases and the indirection markers. Match case-insensitively and "
    "tolerate the OCR damage shown — keywords lose spaces, letters and punctuation.",
    "body")]

story += [section(P("2.1 Expiry labels &mdash; the date we want", "h2"), table([
    ["Canonical", "Variants / OCR-damaged forms seen"],
    ["EXP DATE", "EXP, EXP DATE, EXP.DATE, Exp.Date, ERDATE (mangled), EXP :"],
    ["BEST BEFORE", "Best Before, Best Before Date, BestBefore, Best before, BB"],
    ["EXPIRY DATE", "Expiry date, Date of expiry, Expiry Date"],
    ["USE BEFORE", "Use Before, USP (rare mis-read)"],
], [40 * mm, 126 * mm]))]

story += [section(P("2.2 Manufacture labels &mdash; used only to derive", "h2"), table([
    ["Canonical", "Variants / OCR-damaged forms seen"],
    ["MFG DATE", "MFG DATE, MFG., MFD, MFD(Date), MF9 (mangled), MFO (mangled)"],
    ["MANUFACTURING DATE", "Manufacturing date, Manufact ring Date (mangled)"],
    ["MONTH & YEAR OF MFG", "Month & Year of Manufacturing, Month and year of manufacture"],
], [40 * mm, 126 * mm]))]

story += [section(P("2.3 Decoy labels &mdash; must NOT be picked as expiry", "h2"), table([
    ["Decoy", "Why it is dangerous"],
    ["Import Date / IMPORT DATE", "Looks like a date, often near the expiry (samples 7, 19, 44)"],
    ["Month & Year of Import", "Same; sometimes the only clearly-read date on the panel"],
    ["Packing / print date", "On weighing-scale stickers, an EARLIER date beside the expiry (33/35/37)"],
    ["Batch / Lot No.", "Alphanumeric codes that contain digit runs (2610A250707M046)"],
    ["MRP / price / per kg", "Rs. 680.00 / 272.00 — digit noise on the same sticker"],
], [46 * mm, 120 * mm]))]

story += [section(P("2.4 Shelf-life phrases &mdash; trigger derivation", "h2"), table([
    ["Phrase seen", "Meaning"],
    ["Best Before 1 Year from Mfg. Dt.", "expiry = mfg + 12 months (samples 21, 22)"],
    ["24 months from date of manufacture", "expiry = mfg + 24 months"],
    ["After opening, use within 3 months", "relative to OPENING — not a fixed expiry (sample 27)"],
], [66 * mm, 100 * mm]))]

story += [section(P("2.5 Indirection markers &mdash; no date in this panel", "h2"), table([
    ["Marker", "Seen on"],
    ["as printed on bag / as printed on pack", "24, 32"],
    ["MFG. DATE, BEST BEFORE & BATCH NO. SEE BELOW", "36"],
    ["Mfd. By : See On Pack", "19, 44"],
], [96 * mm, 70 * mm]))]

story += [PageBreak()]

# ============================================================ 3. extraction patterns
story += [P("3. Extraction patterns (structural cases)", "h1")]
story += [P(
    "How the value(s) sit on the panel, and how the parser should resolve each. These "
    "are the cases the rule engine branches on. Rough share of the 44 ground-truthed "
    "images is given to show where the effort pays off.", "body")]

patterns = [
    ("E1", "Direct labelled expiry", "~21 imgs", GOOD,
     "An expiry label (2.1) immediately followed by a value (section 1). The easy, "
     "common case.",
     "EXP DATE:20/11/2026 &nbsp;|&nbsp; Best Before:April 2031 &nbsp;|&nbsp; "
     "Expiry date: 15/12/2027",
     "Take the value after the label. Apply day-inference if month-only."),
    ("E2", "Both dates printed, pick expiry", "~6", GOOD,
     "MFG and Best Before both printed as separate labelled values. No maths — "
     "just pick the expiry-labelled one and ignore MFG.",
     "Month &amp; Year of Manufacturing: July 2025 / Best Before: January 2027",
     "Prefer the expiry label. MFG is there only as a cross-check."),
    ("E3", "Derive from MFG + shelf life", "~4", WARN,
     "Only a manufacture date is printed, plus a shelf-life phrase (2.4). Expiry is "
     "computed.",
     "MFG DATE 30/07/26 + 'Best Before 1 Year from Mfg. Dt.' → 30/07/27",
     "expiry = mfg + N months. Needs a phrase→months map."),
    ("E4", "Derive, but shelf life NOT on panel", "~3", BAD,
     "Manufacture date is read, but the shelf-life statement is absent from the OCR "
     "text (off-panel or not captured). Cannot be derived from this image alone.",
     "sample 7: MFD.DATE:20250110 only; true expiry 10/01/27 needs '+24 months' "
     "known elsewhere",
     "Fall back to a per-SKU shelf-life table keyed by barcode."),
    ("E5", "Compressed MFG-EXP range", "~2", WARN,
     "Two dates joined into one string, mfg first, expiry second. Often month-year.",
     "09/2025-08/2028 → expiry 31/08/2028 &nbsp;|&nbsp; 11/2025-10/2028 (26)",
     "Split on '-', take the later half, apply day-inference."),
    ("E6", "Weighing-scale / price-gun sticker", "~3", WARN,
     "In-store printed sticker: a code, an EARLIER packing date, the expiry (later), "
     "and a time-of-day. All unlabelled.",
     "51434832CA 23/05/2025 / 23/11/2026 23:42 → expiry 23/11/2026",
     "Of the DD/MM/YYYY dates present, the latest is expiry. Strip HH:MM."),
    ("E7", "Two unlabelled dates", "~2", WARN,
     "Two bare dates side by side, no labels (or a shared label). The later is expiry, "
     "since MFG &lt; EXP.",
     "15/06/26 14/06/27 (36) &nbsp;|&nbsp; 22/05/26 22/05/28 (43)",
     "later date wins. This is a heuristic, not a guarantee — low confidence."),
    ("E8", "Combined label, two values", "~1", WARN,
     "One label covering both dates: 'Manufacturing / Best before date :'. Values "
     "usually mashed together by OCR.",
     "Manufacturing / Best before date : 22/05/26 22/05/28 (43)",
     "Split into two dates, later = expiry."),
    ("E9", "Indirection", "~2", BAD,
     "The label is present but the value points elsewhere ('as printed on pack', "
     "'SEE BELOW'). No date to extract here.",
     "Best Before ~ as printed on bag (24) &nbsp;|&nbsp; ...SEE BELOW (36)",
     "Detect the marker → flag for the other panel / manual entry."),
    ("E10", "Use-within-N-of-opening", "~1", BAD,
     "Shelf life is relative to the OPENING event, not manufacture, so no fixed expiry "
     "exists.",
     "After opening, use within 3 months (27)",
     "Do not compute a date. Store as informational only."),
    ("E11", "Missing / blank", "~4", BAD,
     "Labels printed with no values, or nothing date-like read at all.",
     "'Best Before:' and 'Batch No:' printed empty (11, 12); nothing on 8, 28",
     "Flag for manual entry; keep image."),
    ("E12", "Expiry on a different photo", "n/a", BAD,
     "Barcode/MFG on one face, expiry on another. One photo cannot carry both.",
     "samples 46 + 47 — combine to 04/08/27, neither alone yields it",
     "Second-photo path for rigid containers."),
]
for pid, name, share, tone, desc, ex, how in patterns:
    head = Table([[Paragraph(f"<b>{pid} &nbsp; {name}</b>", S["body"]),
                   Paragraph(share, S["small"])]],
                 colWidths=[136 * mm, 30 * mm])
    head.setStyle(TableStyle([
        ("LINEBEFORE", (0, 0), (0, -1), 2.4, tone),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f6f8fb")),
        ("LEFTPADDING", (0, 0), (0, -1), 9), ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    body = [head,
            Paragraph(desc, S["body"]),
            Paragraph(f"<font face='Courier' size=8>{ex}</font>", S["small"]),
            Paragraph(f"<b>Resolve:</b> {how}", S["small"]),
            Spacer(1, 5)]
    story += [section(*body)]

story += [PageBreak()]

# ============================================================ 4. parser algorithm
story += [P("4. Suggested parser flow", "h1")]
story += [P(
    "A first-cut ordering for the deterministic pass. Each step is cheap; the order "
    "matters because it resolves the decoys and indirection before trusting a bare "
    "date.", "body")]
story += [Paragraph(
    "1.  Normalise OCR text: join lines, fix common damage (spaces in keywords).<br/>"
    "2.  Detect indirection markers (2.5) → if found and no direct value, flag "
    "E9 / manual.<br/>"
    "3.  Find all EXPIRY-labelled values (2.1) → E1 / E2. Take it, day-infer, done.<br/>"
    "4.  Else find a RANGE (V9) → E5. Split, later half.<br/>"
    "5.  Else find a shelf-life phrase (2.4) + a MFG date → E3. Compute.<br/>"
    "6.  Else collect all bare dates, drop decoys (2.3) and any date &le; today-ish "
    "MFG → later one wins (E6 / E7). Low confidence.<br/>"
    "7.  Else → E4 / E11: look up shelf life by barcode, or flag for manual entry.",
    S["code"])]
story += [callout(
    "<b>Every derived or heuristic result (E3, E5, E6, E7) is at most medium "
    "confidence and must be confirmed by the employee — never auto-saved.</b> "
    "Only a directly-labelled, cleanly-parsed date (E1/E2) should be a candidate for "
    "auto-save once the pilot proves accuracy. This matches the confidence policy in "
    "the architecture proposal.", GOOD)]

story += [P("Sanity rules worth enforcing", "h2")]
story += [B("Expiry must be in the future, or only recently past.")]
story += [B("Expiry must be after the manufacture date, when both are read.")]
story += [B("Expiry − MFG should fall within the product's plausible shelf life "
            "(e.g. 6–36 months); a 24-month gap on sample 44 is a good cross-check.")]
story += [B("Two captures of the same SKU+batch that disagree → flag, do not "
            "overwrite.")]

# ============================================================ 5. appendix
story += [PageBreak()]
story += [P("5. Appendix &mdash; per-image classification", "h1")]
story += [P(
    "Every sample tagged with its extraction pattern (E-id) and the dominant value "
    "format(s). 'Truth' is the ground-truth expiry (DD/MM/YY); blank where none is "
    "derivable from a single photo. Use this as the parser's test fixture.", "small")]

# name, truth, E-id, value fmt, note
rows_s1 = [
    ("s1/192316", "—", "E1", "V1", "EXP DATE:04/12/2026 + MFG"),
    ("s1/192416", "—", "E1", "V1", "ERDATE (label mangled)"),
    ("s1/192441", "—", "E1", "V1", "Expiry date : 10/11/2027"),
    ("s1/192506", "—", "E4", "V7", "MFD+IMPORT YYYYMMDD, no exp"),
    ("s1/192529", "—", "E11", "—", "Best Before blank"),
    ("s1/192607", "—", "E1", "V1", "Best before:18/06/2025"),
    ("s1/192628", "—", "E1", "V1", "Best before:18/06/2025"),
    ("s1/192642", "—", "E2", "V4", "MFD April26 / BB April31"),
    ("s1/192703", "—", "E2", "V4", "Mfg July25 / BB Jan27"),
]
rows_s2 = [
    ("s2/1", "20/11/26", "E1", "V1", "EXP DATE:20-112026"),
    ("s2/2", "30/04/31", "E1", "V4", "Best Before:April2031"),
    ("s2/3", "30/04/31", "E1", "V4", "BestBefore:April2031"),
    ("s2/4", "30/04/27", "E1", "V4", "BestBefore:April2027"),
    ("s2/5", "12/09/26", "E1", "V1", "EXP DATE:12/09/2026"),
    ("s2/6", "30/04/31", "E1", "V4", "Best Before:April2031"),
    ("s2/7", "10/01/27", "E4", "V7", "MFD 20250110; exp = +24mo off-panel"),
    ("s2/8", "17/02/27", "E11", "—", "nothing date-like read"),
    ("s2/9", "31/01/27", "E2", "V4", "Mfg July25 / BB Jan27"),
    ("s2/10", "03/03/27", "E1", "V1", "Bestbefore:03-03-2027"),
    ("s2/11", "28/02/27", "E1", "V4", "EXP.FEB 2027 (below blank)"),
    ("s2/12", "28/02/27", "E11", "—", "all date labels blank this shot"),
    ("s2/13", "28/02/27", "E1", "V4", "EXP.FEB 2027 (cut-off pack)"),
    ("s2/14", "28/02/27", "E1", "V4", "EXP FEB 2027"),
    ("s2/15", "28/02/27", "E1", "V4", "EXP FEB 2027"),
    ("s2/16", "11/09/26", "E11", "—", "only BATCH read"),
    ("s2/17", "10/03/27", "E1", "V1", "dot-matrix EXP faint on jar"),
    ("s2/18", "23/07/27", "E1", "V1", "EXP/MFG labels, values missed"),
    ("s2/19", "28/02/29", "E1", "V5", "Expiry Date:FEB-2029 (+Import decoy)"),
    ("s2/20", "13/11/27", "E1", "V1", "EXP:13/11/2027 (poorly read)"),
    ("s2/21", "30/07/27", "E3", "V1", "MFG 30/07/26 + '1 Year from Mfg'"),
    ("s2/22", "28/07/27", "E3", "V1", "MFG 28/07/26 + '1 Years from Mfg'"),
    ("s2/23", "07/03/27", "E1", "V1", "Use Before: 07/03/2027"),
    ("s2/24", "—", "E9", "—", "Best Before ~ as printed on bag"),
    ("s2/25", "31/10/27", "E1", "V3", "Best Before : 10/2027"),
    ("s2/26", "31/10/28", "E5", "V9", "11/2025-10/2028 (range)"),
    ("s2/27", "—", "E10", "—", "use within 3 months of opening"),
    ("s2/28", "31/10/26", "E11", "—", "nothing read"),
    ("s2/29", "31/08/28", "E5", "V9", "09/2025-08/2028 (range)"),
    ("s2/30", "18/02/27", "E1", "V1", "Best Before Date: 18-02-2027"),
    ("s2/31", "15/12/27", "E1", "V1", "Expiry date: 15/12/2027"),
    ("s2/32", "—", "E9", "—", "Best Before: As printed on pack"),
    ("s2/33", "13/08/27", "E6", "V1", "weighing sticker, later date+time"),
    ("s2/34", "04/09/27", "E1", "V6", "Best Before 04 September 2027"),
    ("s2/35", "23/11/26", "E6", "V1", "weighing sticker 23/11/2026 23:42"),
    ("s2/36", "14/06/27", "E7", "V1", "15/06/26 14/06/27 + SEE BELOW"),
    ("s2/37", "28/11/26", "E6", "V1", "weighing sticker"),
    ("s2/38", "22/05/27", "E1", "V2", "MFG28/11/25;EXP22/05/27"),
    ("s2/39", "21/01/28", "E1", "V8", "EXP2028.JAN.21"),
    ("s2/40", "30/04/31", "E1", "V4", "Best Before: April 2031"),
    ("s2/41", "22/06/28", "E1", "V1", "Date of expiry : 22/06/2028"),
    ("s2/42", "18/05/26", "E1", "V7", "EXP20260518"),
    ("s2/43", "22/05/28", "E8", "V2", "combined label, two dates"),
    ("s2/44", "29/02/28", "E1", "V5", "Expiry Date:FEB-2028 (leap!) +decoy"),
    ("s2/45", "30/04/31", "E1", "V4", "Best Before:April 2031"),
    ("s2/46", "—", "E12", "V2", "MFG only; pairs with s2/47"),
    ("s2/47", "—", "E12", "—", "barcode face only"),
    ("s2/48", "23/07/27", "E1", "V1", "EXP :23/07/2027"),
    ("s2/49", "23/07/27", "E1", "V1", "EXP:23/07/2027"),
]

header = ["Image", "Truth", "E", "Fmt", "Dominant OCR evidence"]
w = [24 * mm, 20 * mm, 10 * mm, 12 * mm, 100 * mm]


def appendix_table(rows):
    return table([header] + [list(r) for r in rows], w, mono_cols=(1, 4))


story += [P("samples1/ (barcode-benchmark set, no ground truth)", "h2")]
story += [appendix_table(rows_s1)]
story += [P("samples2/ (expiry-benchmark set, with ground truth)", "h2")]
story += [appendix_table(rows_s2)]

story += [Spacer(1, 6)]
story += [P("Pattern frequency (44 ground-truthed images): E1 direct ≈ 21 · "
            "E2 both-printed ≈ 4 · E3 derive ≈ 2 · E4 derive-no-shelf-life "
            "≈ 2 · E5 range ≈ 2 · E6 weighing-sticker ≈ 3 · "
            "E7/E8 two-date ≈ 3 · E9 indirection ≈ 2 · E10 open-life "
            "≈ 1 · E11 missing ≈ 4. Counts are approximate — a few "
            "images are OCR-limited rather than pattern-limited.", "small")]


# ============================================================ build
def furniture(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.6)
    canvas.line(22 * mm, h - 16 * mm, w - 22 * mm, h - 16 * mm)
    canvas.setFont("Helvetica", 7.6)
    canvas.setFillColor(MUTED)
    canvas.drawString(22 * mm, h - 13.4 * mm, "Expiry-Date Pattern Specification")
    canvas.drawRightString(w - 22 * mm, h - 13.4 * mm, "JustDogs")
    canvas.line(22 * mm, 15 * mm, w - 22 * mm, 15 * mm)
    canvas.drawString(22 * mm, 11 * mm,
                      f"For the deterministic parser · {date.today():%d %b %Y}")
    canvas.drawRightString(w - 22 * mm, 11 * mm, f"Page {doc.page}")
    canvas.restoreState()


def main():
    doc = BaseDocTemplate(str(OUT), pagesize=A4,
                          leftMargin=22 * mm, rightMargin=22 * mm,
                          topMargin=22 * mm, bottomMargin=20 * mm,
                          title="Expiry-Date Pattern Specification", author="JustDogs")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=furniture)])
    doc.build(story)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
