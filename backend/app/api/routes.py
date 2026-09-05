"""Capture endpoints.

Both handlers are plain `def`, not `async def`. The work here is ~600ms of
blocking CPU (OCR dominates); inside an `async def` that would block the
event loop and the server would serve one request at a time. Declaring
them `def` makes FastAPI run them in its threadpool, so requests stay
concurrent.
"""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from ..config import MAX_UPLOAD_BYTES
from ..ocr import is_loaded
from ..scanner import scan_bytes
from .schemas import HealthResponse, ScanResponse

router = APIRouter()

VERSION = "0.1.0"


@router.get("/health", response_model=HealthResponse, tags=["ops"])
def health() -> HealthResponse:
    """Liveness plus whether the OCR models are resident.

    models_loaded is false only in the window before warmup finishes; a
    request served then still works, it just pays the load cost once.
    """
    return HealthResponse(status="ok", models_loaded=is_loaded(),
                          version=VERSION)


@router.post("/scan", response_model=ScanResponse, tags=["capture"])
def scan_upload(file: UploadFile = File(..., description="A photo of the pack")
                ) -> ScanResponse:
    """Read barcode(s) and the expiry date from one uploaded photograph.

    Stateless: nothing is stored. The frontend holds the two-slot session
    (product_id, expiry_date) and merges whatever each call returns, so
    two photos of one product need no server-side session.
    """
    data = file.file.read()

    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail={"error": "empty_upload",
                                    "message": "No image data received."})
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"error": "too_large",
                    "message": f"Image is {len(data) // 1024} KB; the limit is "
                               f"{MAX_UPLOAD_BYTES // 1024 // 1024} MB. "
                               "Resize to 1600px before uploading.",
                    "max_bytes": MAX_UPLOAD_BYTES})

    try:
        result = scan_bytes(data, name=file.filename or "upload")
    except ValueError as exc:
        # Not a decodable image -- a wrong file type, or a truncated upload.
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            detail={"error": "unreadable_image",
                                    "message": str(exc)}) from exc

    return ScanResponse(**result)
