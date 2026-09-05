"""Deterministic expiry-date parser.

Turns raw OCR text lines into a normalised expiry date, using only rules
derived from the pattern specification in
backend/tests/ocr_expiry/Expiry_Date_Pattern_Spec.pdf.
"""
from .parser import parse
from .types import Confidence, ExpiryResult, Pattern, Role

__all__ = ["parse", "ExpiryResult", "Confidence", "Pattern", "Role"]
