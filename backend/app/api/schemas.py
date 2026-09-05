"""Response models for the capture API.

These mirror the dict that scanner.scan() already returns. Declaring them
gives the frontend a typed contract and free OpenAPI docs at /docs, which
matters here because the response is the whole product of this service.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class Box(BaseModel):
    """Axis-aligned box in ORIGINAL image pixels."""
    x: int
    y: int
    w: int
    h: int


class BoxNorm(BaseModel):
    """Same box as fractions of image width/height.

    Use this one for overlays: it survives any display resize, so the
    frontend does not need to know the original pixel dimensions.
    """
    x: float
    y: float
    w: float
    h: float


class BarcodeValue(BaseModel):
    value: str
    format: str = Field(description="EAN13, QRCode, ...")
    is_retail: bool = Field(
        description="Only retail formats may be used as a product_id. "
                    "A QR code on a hang tag decodes but identifies nothing.")
    box: Box
    box_norm: BoxNorm
    corners: list[list[int]] = Field(
        description="Exact quad, for a barcode rotated in frame.")


class BarcodeBlock(BaseModel):
    ok: bool
    count: int
    retail_count: int = 0
    values: list[BarcodeValue] = []
    ms: float
    error: str | None = None


class OcrBlock(BaseModel):
    ok: bool
    line_count: int
    lines: list[str] = Field(description="Raw text, in detection order.")
    ms: float
    error: str | None = None


class ExpiryBlock(BaseModel):
    expiry: str | None = Field(description="ISO date, or null if unresolved.")
    manufacture: str | None = None
    pattern: str | None = Field(
        default=None,
        description="Extraction pattern used (E1..E11). Drives the retry "
                    "message the frontend shows on failure.")
    confidence: str = Field(description="high | medium | none")
    needs_review: bool = Field(
        description="True unless the date was directly labelled and cleanly "
                    "parsed. Never auto-save when this is true.")
    reason: str = ""
    warnings: list[str] = []
    shelf_life_months: int | None = None
    candidates: list[str] = []


class ImageSize(BaseModel):
    w: int
    h: int


class ScanResponse(BaseModel):
    image: str
    image_size: ImageSize
    barcode: BarcodeBlock
    ocr: OcrBlock
    expiry: ExpiryBlock
    ms_total: float


class HealthResponse(BaseModel):
    status: str
    models_loaded: bool
    version: str
