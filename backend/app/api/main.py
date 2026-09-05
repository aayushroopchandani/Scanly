"""FastAPI application for the Scanify capture pipeline.

    uvicorn app.api.main:app --reload      (from backend/)

Phase 1 scope: read a photo, return barcode(s) and a parsed expiry date.
Nothing is persisted -- no images, no logs, no database. Writing the
confirmed expiry back to the inventory system is Phase 2.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import CORS_ORIGINS
from ..ocr import warmup
from .routes import VERSION, router

log = logging.getLogger("scanify")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the OCR models before the first request arrives.

    Constructing RapidOCR reads the ONNX detection and recognition models
    from disk -- measured at ~3.8s cold. Paying that at boot rather than
    on an employee's first photo is the difference between a snappy tool
    and one that looks broken the first time it is used.
    """
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    log.info("loading OCR models...")
    seconds = warmup()
    log.info("OCR models ready in %ss", seconds)
    yield
    log.info("shutting down")


app = FastAPI(
    title="Scanify Capture API",
    version=VERSION,
    summary="Read a product barcode and its printed expiry date from a photo.",
    lifespan=lifespan,
)

# The PWA is served from a different origin; without this the browser
# blocks every call with no useful error. Tighten before deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router)
