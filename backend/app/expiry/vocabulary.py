"""Label words, shelf-life phrases and indirection markers.

Pure data, straight from section 2 of the pattern specification. Adding a
new supplier's wording should mean editing THIS file only.

Matching happens against a space-stripped uppercase form of the line, so
OCR damage that eats spaces ("BestBefore", "Monthandyearofmanufacture")
still matches without extra entries.
"""
from __future__ import annotations

import re

# --- 2.1 expiry labels: the date we actually want ----------------------
EXPIRY_LABELS = [
    "BESTBEFOREDATE", "BESTBEFORE", "BESTBEFOR", "BSTBEFORE",
    "DATEOFEXPIRY", "EXPIRYDATE", "EXPIRY", "EXPDATE", "EXPDT",
    "USEBEFORE", "USEBY",
    "EXP", "BB",
    # OCR-damaged spellings of "EXP" / "EXP DATE" observed in the samples.
    "ERDATE", "EAPDATE", "EAPDTE", "EPDATE", "EXF", "EXP0",
]

# --- 2.2 manufacture labels: used only to derive -----------------------
MANUFACTURE_LABELS = [
    "MONTHANDYEAROFMANUFACTURE", "MONTHYEAROFMANUFACTURING",
    "MONTHANDYEAROFMANUFACTURING", "MONTHYEAROFMANUFACTURE",
    "MANUFACTURINGDATE", "MANUFACTURINGDT", "MANUFACTRINGDATE",
    "DATEOFMFG", "MFGDATE", "MFDDATE", "MFDDATE", "MFDATE",
    "MFGDHTE", "MFGDT",
    "MFD", "MFG", "MF9", "MFO", "MF0",
]

# --- 2.3 decoy labels: look like dates, must never be the answer -------
DECOY_LABELS = [
    "MONTHANDYEAROFIMPORT", "MONTHYEAROFIMPORT", "MONTHOFIMPORT",
    "IMPORTMONTH", "IMPORTDATE", "IMPORTEDDATE", "DATEOFIMPORT",
    # OCR routinely turns the leading I into J or 1.
    "JMPORTDATE", "1MPORTDATE", "JMPORT",
    "IMPORT",
    "BATCHNO", "BATCHNUMBER", "BATCHCODE", "BARTCHNO", "BATCH",
    "LOTNO", "LOTCODE", "LOT",
]

# --- 2.4 shelf-life phrases: trigger derivation (E3) -------------------
# Matched against the space-stripped uppercase line.
# Deliberately tolerant: OCR turns "FROM" into "FRON" and "DATE OF" into
# "DATECF" (sample 7). Anchoring on the number plus the unit is enough,
# because these phrases only ever appear next to a shelf-life statement.
SHELF_LIFE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"BESTBEFORE(\d{1,2})YEARS?"), "years"),
    (re.compile(r"(\d{1,2})YEARS?FRO[MN]"), "years"),
    (re.compile(r"BESTBEFORE(\d{1,2})MONTHS?"), "months"),
    (re.compile(r"(\d{1,3})MONTHS?FRO[MN]"), "months"),
]

# --- 2.4b relative-to-OPENING: no fixed expiry exists (E10) ------------
OPENING_LIFE = re.compile(r"AFTEROPENING.*?USEWITHIN(\d+)(MONTH|YEAR)")

# --- 2.5 indirection markers: no value on this panel (E9) -------------
INDIRECTION_MARKERS = [
    "ASPRINTEDONPACK", "ASPRINTEDONBAG", "ASPRINTEDONPOUCH",
    "SEEBELOW", "SEEONPACK", "SEEADDRESSPANEL", "PRINTEDONPACK",
]


def _compile(labels: list[str]) -> re.Pattern[str]:
    """Longest-first so 'BESTBEFOREDATE' wins over 'BESTBEFORE'."""
    ordered = sorted(set(labels), key=len, reverse=True)
    return re.compile("|".join(re.escape(w) for w in ordered))


EXPIRY_RE = _compile(EXPIRY_LABELS)
MANUFACTURE_RE = _compile(MANUFACTURE_LABELS)
DECOY_RE = _compile(DECOY_LABELS)
INDIRECTION_RE = _compile(INDIRECTION_MARKERS)
