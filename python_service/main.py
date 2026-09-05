"""
main.py - FastAPI Microservice for ID Card Information Extraction.
Exposes REST endpoints for image preprocessing, OCR, Decision Gate check,
Groq LLM extraction, Pydantic validation, and Human-in-the-Loop Confirmation Gateway.
"""

import io
import os
from contextlib import asynccontextmanager

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

try:
    import torch
    torch.set_num_threads(1)
except Exception:
    pass

from typing import Optional, Dict, Any
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from PIL import Image
import numpy as np
from dotenv import load_dotenv

load_dotenv()

from schemas import FinalExtractionResult, UnsupportedDocumentData, ConfirmationRequest
from preprocessing import (
    assess_image_quality, 
    preprocess_id_card, 
    extract_portrait_photo, 
    preprocess_deep_multi_pass
)
from ocr_engine import extract_ocr_data, draw_bounding_boxes, check_tesseract_available, get_ocr_reader
from document_classifier import classify_document_heuristics
from llm_extractor import extract_document_info, get_available_models
from validation import validate_and_clean_extraction
from utils import pil_to_cv2, cv2_to_base64, logger
from storage import (
    save_confirmed_verification, 
    save_extraction,
    get_history, 
    get_failed_history,
    get_extraction_by_id, 
    delete_extraction_by_id, 
    get_storage_stats, 
    clean_storage
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm RapidOCR engine on startup."""
    try:
        logger.info("Initializing and pre-warming RapidOCR ONNX engine...")
        get_ocr_reader()
        logger.info("RapidOCR engine initialized successfully.")
    except Exception as e:
        logger.warning(f"RapidOCR warmup warning: {e}")
    yield


app = FastAPI(
    title="Utility Bot - Verification Document API",
    version="3.1.0",
    description="Utility Bot backend providing Aadhaar, PAN, and Driving Licence verification with Human-in-the-Loop Confirmation Gateway, 30-day auto-retention, photo storage, and Device ID isolation.",
    lifespan=lifespan
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Health check endpoint reporting OCR & database status."""
    ocr_available, ocr_msg = check_tesseract_available()
    from storage import MONGODB_URI
    return {
        "status": "healthy",
        "service": "utility_bot_backend",
        "ocr_engine": "RapidOCR (ONNX)",
        "ocr_available": ocr_available,
        "ocr_message": ocr_msg,
        "database_connected": True,
        "database_type": "MongoDB Atlas" if MONGODB_URI else "Local Store (history.json)",
        "mongodb_configured": bool(MONGODB_URI),
        "tesseract_available": ocr_available,
        "tesseract_message": ocr_msg
    }


@app.get("/models")
def list_models(api_key: Optional[str] = None):
    """Lists available LLM extraction models."""
    return {"models": get_available_models(api_key)}


@app.get("/history")
def list_history(
    limit: int = 50, 
    page: int = 1, 
    doc_type: Optional[str] = None,
    deviceId: Optional[str] = None,
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id")
):
    """Retrieves verified SUCCESS verification records ('IMG...' series) strictly for the public History drawer."""
    active_device = x_device_id or deviceId
    return get_history(limit=limit, page=page, doc_type=doc_type, device_id=active_device)


@app.get("/failed-history")
def list_failed_history(
    limit: int = 50,
    page: int = 1,
    deviceId: Optional[str] = None,
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id")
):
    """Retrieves FAILED verification audit records ('FAIL...' series) strictly hidden from public history."""
    active_device = x_device_id or deviceId
    return get_failed_history(limit=limit, page=page, device_id=active_device)


@app.get("/history/{doc_id}")
def retrieve_extraction(
    doc_id: str,
    deviceId: Optional[str] = None,
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id")
):
    """Retrieves a single verification record by ID."""
    active_device = x_device_id or deviceId
    record = get_extraction_by_id(doc_id, device_id=active_device)
    if not record:
        raise HTTPException(status_code=404, detail="Document verification record not found or inaccessible for this device.")
    return record


@app.delete("/history/{doc_id}")
def remove_extraction(
    doc_id: str,
    deviceId: Optional[str] = None,
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id")
):
    """Deletes a verification record by ID."""
    active_device = x_device_id or deviceId
    success = delete_extraction_by_id(doc_id, device_id=active_device)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found or permission denied.")
    return {"message": "Document deleted successfully."}


@app.get("/storage/stats")
def storage_usage_stats(
    deviceId: Optional[str] = None,
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id")
):
    """Returns storage usage statistics."""
    active_device = x_device_id or deviceId
    return get_storage_stats(device_id=active_device)


@app.post("/storage/clean")
def trigger_storage_cleanup(
    force_all: bool = False,
    deviceId: Optional[str] = None,
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id")
):
    """Cleans expired records or purges verification storage."""
    active_device = x_device_id or deviceId
    return clean_storage(device_id=active_device, force_all=force_all)


@app.post("/confirm")
def confirm_verification_decision(
    payload: ConfirmationRequest,
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id")
):
    """
    Human-in-the-Loop Confirmation Gateway endpoint:
    - 'correct': Assigns sequential ID 'IMG000001', sets status='Success', saves to 'verifications' (Visible in History).
    - 'wrong': Assigns sequential ID 'FAIL000001', sets status='Failed', saves to 'failed_verifications' (Hidden from History).
    """
    active_device = x_device_id or payload.deviceId or "default_client"
    res = save_confirmed_verification(
        result_dict=payload.model_dump() if hasattr(payload, "model_dump") else payload.dict(),
        action=payload.action,
        edited_data=payload.data,
        original_filename=payload.original_filename or "document.jpg",
        thumbnail_image=payload.thumbnail_image,
        portrait_photo=payload.portrait_photo,
        device_id=active_device
    )
    return res


@app.post("/extract", response_model=FinalExtractionResult)
def extract_document(
    file: UploadFile = File(...),
    min_confidence: float = Form(25.0),
    psm_mode: int = Form(11),
    enable_glare: bool = Form(True),
    enable_clahe: bool = Form(True),
    enable_denoise: bool = Form(True),
    enable_threshold: bool = Form(False),
    threshold_method: str = Form("otsu"),
    deep_scan: bool = Form(False),
    model_name: Optional[str] = Form(None),
    groq_api_key: Optional[str] = Form(None),
    deviceId: Optional[str] = Form(None),
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id")
):
    """
    Main extraction pipeline endpoint with Pre-LLM Decision Gate.
    1. Reads & validates uploaded image.
    2. Runs quality & blur assessment.
    3. Runs OpenCV preprocessing (or Deep Multi-Pass Scan if deep_scan=True).
    4. Extracts portrait photo thumbnail.
    5. Runs local OCR & draws bounding boxes.
    6. DECISION GATE: Evaluates document signatures. If unsupported, short-circuits immediately.
    7. Calls Groq LLM or Pure OCR Regex Engine.
    8. Validates & normalizes fields (Pydantic / Regex).
    9. Returns structured JSON with status='Pending Confirmation'.
    """
    # 1. Validate file format
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a valid image (JPG, JPEG, PNG).")

    try:
        contents = file.file.read()
        pil_image = Image.open(io.BytesIO(contents))
        if pil_image.mode not in ("RGB", "L"):
            pil_image = pil_image.convert("RGB")
        cv2_orig = pil_to_cv2(pil_image)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to decode image: {str(e)}")

    # 2. Image Quality & Blur Check
    quality_report = assess_image_quality(cv2_orig)

    # 3. Portrait Face Crop Extraction
    portrait_photo = extract_portrait_photo(cv2_orig)

    # 4. OpenCV Preprocessing (Standard vs. Deep Multi-Pass)
    if deep_scan:
        logger.info("[Vision Pipeline] Running High-Accuracy Deep Multi-Pass scan...")
        cv2_preprocessed = preprocess_deep_multi_pass(cv2_orig)
    else:
        cv2_preprocessed = preprocess_id_card(
            cv2_orig,
            enable_resize=True,
            enable_clahe=enable_clahe,
            enable_denoise=enable_denoise,
            enable_glare_reduction=enable_glare,
            enable_threshold=enable_threshold,
            threshold_method=threshold_method
        )

    # 5. RapidOCR with Bounding Boxes (Free & Local)
    try:
        ocr_result = extract_ocr_data(
            cv2_preprocessed,
            min_confidence=min_confidence,
            psm_mode=psm_mode
        )
        cv2_annotated = draw_bounding_boxes(cv2_orig, ocr_result, show_confidence=True)
    except Exception as e:
        logger.error(f"OCR Error: {e}")
        raise HTTPException(status_code=500, detail=f"OCR Processing failed: {str(e)}")

    # Encode images for visual pipeline
    pipeline_images = {
        "original": cv2_to_base64(cv2_orig, quality=80),
        "preprocessed": cv2_to_base64(cv2_preprocessed, quality=80),
        "annotated": cv2_to_base64(cv2_annotated, quality=85)
    }

    # If no readable text was detected at all
    if ocr_result.word_count == 0 or not ocr_result.raw_text.strip():
        unsupported = UnsupportedDocumentData(
            document_type="unsupported",
            error="No readable text detected in the image. Please verify lighting and focus."
        )
        return FinalExtractionResult(
            document_type="unsupported",
            is_valid=False,
            status="Pending Confirmation",
            short_circuited=True,
            data=unsupported,
            warnings=["No text detected by OCR engine."],
            ocr_confidence=0.0,
            raw_ocr_text="",
            quality_report=quality_report,
            images=pipeline_images,
            portrait_photo=portrait_photo
        )

    # 6. DECISION GATE: Heuristic Type Check (Pre-LLM Resource Gate)
    heuristic_type, heuristic_conf, heuristic_scores = classify_document_heuristics(ocr_result.raw_text)
    
    # If the document shows NO resemblance to Aadhaar, PAN, or DL, short-circuit immediately
    if heuristic_type == "unsupported" and max(heuristic_scores.values()) == 0:
        logger.info("[Decision Gate] Document rejected before LLM call. Zero ID keywords found.")
        unsupported = UnsupportedDocumentData(
            document_type="unsupported",
            error="Decision Gate: Document does not match Indian Aadhaar, PAN, or Driving Licence patterns. LLM processing skipped."
        )
        res = FinalExtractionResult(
            document_type="unsupported",
            is_valid=False,
            status="Pending Confirmation",
            short_circuited=True,
            data=unsupported,
            warnings=["Rejected by Pre-LLM Decision Gate (Non-ID document detected)."],
            ocr_confidence=ocr_result.average_confidence,
            raw_ocr_text=ocr_result.raw_text,
            quality_report=quality_report,
            images=pipeline_images,
            portrait_photo=portrait_photo
        )
        return res

    # 7. Groq LLM API Call (Only for supported IDs)
    heuristic_hint_str = f"Found pattern matching for: {heuristic_type.upper()}" if heuristic_type != "unsupported" else None
    
    raw_llm_json, llm_error = extract_document_info(
        ocr_raw_text=ocr_result.raw_text,
        ocr_layout_text=ocr_result.layout_text,
        api_key=groq_api_key,
        model_name=model_name,
        heuristic_hint=heuristic_hint_str
    )

    if raw_llm_json.get("document_type") == "unsupported" and heuristic_type != "unsupported":
        raw_llm_json["document_type"] = heuristic_type

    # 8. Post-Validation and Pydantic Normalization
    final_result = validate_and_clean_extraction(
        raw_data=raw_llm_json,
        ocr_confidence=ocr_result.average_confidence,
        raw_ocr_text=ocr_result.raw_text,
        quality_report=quality_report,
        images=pipeline_images,
        short_circuited=False,
        portrait_photo=portrait_photo
    )

    return final_result


# -----------------------------------------------------------------------------
# Unified Full-Stack Serving: React Client + FastAPI Backend in One Service
# -----------------------------------------------------------------------------
DIST_DIR = os.path.join(os.path.dirname(__file__), "..", "client", "dist")
if not os.path.exists(DIST_DIR):
    DIST_DIR = os.path.join(os.path.dirname(__file__), "dist")

if os.path.exists(DIST_DIR):
    assets_dir = os.path.join(DIST_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith(("docs", "openapi.json", "redoc")):
            raise HTTPException(status_code=404, detail="Not found")
        file_path = os.path.join(DIST_DIR, full_path)
        if full_path and os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        index_file = os.path.join(DIST_DIR, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Frontend not built. Run 'npm run build' in client directory.")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
